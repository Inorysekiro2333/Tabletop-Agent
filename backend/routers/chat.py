"""
Chat Router - WebSocket 实时聊天
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import asyncio
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

from database import get_db
from models.user import User
from models.campaign import Campaign
from models.character import Character
from models.ai_config import AIConfig
from models.save import SessionLog
from models.chat_branch import ChatBranch
from utils.security import get_current_user, verify_token
from services.ai_gateway import AIGateway
from services.chat_session import ChatSessionManager, ChatSession
from services.dice import parse_dice_command, format_dice_result

router = APIRouter(tags=["Chat"])


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # campaign_id -> set of WebSockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, campaign_id: int):
        """接受连接"""
        await websocket.accept()
        if campaign_id not in self.active_connections:
            self.active_connections[campaign_id] = set()
        self.active_connections[campaign_id].add(websocket)

    def disconnect(self, websocket: WebSocket, campaign_id: int):
        """断开连接"""
        if campaign_id in self.active_connections:
            self.active_connections[campaign_id].discard(websocket)
            if not self.active_connections[campaign_id]:
                del self.active_connections[campaign_id]

    async def broadcast(self, campaign_id: int, message: dict):
        """广播消息到所有连接"""
        if campaign_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[campaign_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.add(connection)
            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[campaign_id].discard(conn)


manager = ConnectionManager()


async def generate_opening_story(campaign: Campaign, user: User, session: ChatSession):
    """生成开场故事和招呼语"""
    # 如果开场已生成（或从存档加载了消息），跳过
    if session.story_generated:
        logger.info(f"开场已生成或已从存档加载，跳过生成")
        return

    if not campaign.ai_config_id:
        return

    from database import SessionLocal
    db = SessionLocal()
    try:
        ai_config = db.query(AIConfig).filter(AIConfig.id == campaign.ai_config_id).first()
        if not ai_config:
            return

        # 构建开场提示词
        character_info = ""
        if user.username:
            character_info = f"玩家用户名: {user.username}"

        opening_prompt = f"""你是KP（主持人），请为这个TRPG战役创作一段精彩的开场。

战役信息：
- 名称：{campaign.title}
- 描述：{campaign.description or '暂无描述'}
- 玩家：{character_info}

请根据以上信息，用富有感染力的文字创作一段开场白，介绍故事背景、场景，让玩家身临其境。字数控制在200-300字左右。

开场白应该：
1. 描述一个引人入胜的场景
2. 设定氛围（神秘、紧张、冒险等）
3. 给玩家一个明确的切入点
4. 使用第二人称"你"来描述

请直接输出开场白内容，不要加标题或前缀。"""

        messages = [
            {"role": "system", "content": session.get_full_system_prompt() if session.get_full_system_prompt() else "你是一个TRPG游戏的主持人(KP)。"},
            {"role": "user", "content": opening_prompt}
        ]

        thinking_id = str(uuid.uuid4())

        # 发送思考中状态
        await manager.broadcast(campaign.id, {
            "type": "kp_thinking",
            "id": thinking_id,
            "content": "KP 正在构思开场..."
        })

        # 调用 AI (流式)
        try:
            logger.info(f"开始调用 AI: provider={ai_config.provider.value}, model={ai_config.model_name}, messages_count={len(messages)}")

            full_response = ""
            async for chunk in AIGateway.chat_stream(
                provider_name=ai_config.provider.value.lower(),
                messages=messages,
                model=ai_config.model_name,
                api_key=ai_config.api_key,
                base_url=ai_config.base_url
            ):
                full_response += chunk
                # 发送增量更新
                await manager.broadcast(campaign.id, {
                    "type": "kp_thinking_chunk",
                    "id": thinking_id,
                    "content": chunk
                })

            logger.info(f"AI 开场生成成功: response_length={len(full_response)}")

            # 广播 KP 开场
            await manager.broadcast(campaign.id, {
                "type": "kp_response",
                "thinking_id": thinking_id,
                "role": "kp",
                "content": full_response
            })

            # 记录消息
            session.add_message("kp", full_response)
            session.story_generated = True  # 标记开场已生成

            # 保存到数据库
            log = SessionLog(
                campaign_id=campaign.id,
                session_number=session.game_state.session_number,
                branch_id=session.current_branch_id,
                role="kp",
                content=full_response
            )
            db.add(log)
            db.commit()

        except Exception as e:
            logger.error(f"AI 开场生成失败: {type(e).__name__}: {str(e)}")
            await manager.broadcast(campaign.id, {
                "type": "error",
                "content": f"AI 开场生成失败: {type(e).__name__}: {str(e)}"
            })

    finally:
        db.close()


def get_user_from_token(token: str) -> User:
    """从 token 获取用户"""
    user_id = verify_token(token)
    if not user_id:
        raise ValueError("Invalid token")

    # 直接创建 session 获取用户
    from database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")
        return user
    finally:
        db.close()


@router.websocket("/ws/chat/{campaign_id}")
async def websocket_chat(websocket: WebSocket, campaign_id: int, token: str = None):
    """WebSocket 聊天端点"""

    # 验证用户
    try:
        if not token:
            await websocket.close(code=4001, reason="Missing token")
            return
        user = get_user_from_token(token)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # 验证战役访问权限
    from database import SessionLocal
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(
            Campaign.id == campaign_id,
            Campaign.user_id == user.id
        ).first()
        if not campaign:
            await websocket.close(code=4003, reason="Campaign not found")
            return

        # 获取或创建会话
        session = ChatSessionManager.get_or_create_session(campaign_id)

        # 设置系统提示词
        if campaign.system_prompt:
            session.set_system_prompt(campaign.system_prompt)

        # 设置 AI 配置
        if campaign.ai_config_id:
            session.ai_config_id = campaign.ai_config_id

        # 获取角色信息
        if campaign.ai_config_id:
            ai_config = db.query(AIConfig).filter(AIConfig.id == campaign.ai_config_id).first()
            if ai_config:
                session.ai_config_id = ai_config.id

        # 加载用户角色数据到会话（用于状态追踪）
        character = db.query(Character).filter(
            Character.user_id == user.id
        ).first()
        if character:
            session.set_character_stats(
                character_name=character.name,
                hp=character.hp or 10,
                ac=character.ac or 10,
                level=character.level or 1,
                attributes=character.attributes or {},
                player_name=user.username or ""
            )
            # P0-1: 注入完整角色数据到 AI 上下文
            char_data = {
                "id": character.id,
                "name": character.name,
                "race": character.race or "",
                "character_class": character.character_class or "",
                "level": character.level or 1,
                "backstory": character.backstory or "",
                "personality": character.personality or {},
                "skills": character.skills or [],
                "attributes": character.attributes or {},
                "hp": character.hp or 10,
                "ac": character.ac or 10,
                "equipment": getattr(character, 'equipment', '') or '',
            }
            session.set_selected_character(char_data)

        # 如果数据库中有历史消息，加载它们并标记为已生成开场
        session.load_messages_from_db(campaign_id, db)

    finally:
        db.close()

    await manager.connect(websocket, campaign_id)

    # 发送欢迎消息
    await websocket.send_json({
        "type": "system",
        "content": f"已连接到战役: {campaign.title}",
        "timestamp": str(db.query(Campaign).get(campaign_id).created_at)
    })

    # 如果有历史消息（从数据库加载的），发送给前端
    if session.story_generated:
        # 先发送清空消息，让前端清空现有消息
        await websocket.send_json({
            "type": "history_clear",
            "content": ""
        })
        # 然后发送历史消息
        for msg in session.messages:
            await websocket.send_json({
                "type": "kp_response" if msg.role == "kp" else "player_message",
                "role": msg.role,
                "content": msg.content
            })
        logger.info(f"发送了 {len(session.messages)} 条历史消息给前端")

    # 自动生成开场故事（如果没有历史消息）
    await generate_opening_story(campaign, user, session)

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            msg_type = message_data.get("type", "player_message")
            content = message_data.get("content", "")

            if msg_type == "player_message":
                await handle_player_message(websocket, campaign_id, user, content, session)
            elif msg_type == "roll_dice":
                await handle_roll_command(websocket, campaign_id, content)
            elif msg_type == "load_save":
                await handle_load_save(websocket, campaign_id, user, message_data.get("save_id"))
            elif msg_type == "select_character":
                await handle_select_character(websocket, campaign_id, user, message_data.get("character_id"), session)
            elif msg_type == "save_game":
                await handle_save_game(websocket, campaign_id, user, message_data, session)
            elif msg_type == "branch_create":
                await handle_branch_create(websocket, campaign_id, user, message_data, session)
            elif msg_type == "branch_switch":
                await handle_branch_switch(websocket, campaign_id, user, message_data, session)
            elif msg_type == "branch_list":
                await handle_branch_list(websocket, campaign_id, user, session)

    except WebSocketDisconnect:
        manager.disconnect(websocket, campaign_id)
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "content": f"Error: {str(e)}"
        })
        manager.disconnect(websocket, campaign_id)


async def handle_select_character(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    character_id: int,
    session: ChatSession
):
    """处理角色选择 —— P0-1: 将完整角色数据注入 AI 上下文"""
    if not character_id:
        return

    from database import SessionLocal
    db = SessionLocal()
    try:
        character = db.query(Character).filter(
            Character.id == character_id,
            Character.user_id == user.id
        ).first()
        if character:
            char_data = {
                "id": character.id,
                "name": character.name,
                "race": character.race or "",
                "character_class": character.character_class or "",
                "level": character.level or 1,
                "backstory": character.backstory or "",
                "personality": character.personality or {},
                "skills": character.skills or [],
                "attributes": character.attributes or {},
                "hp": character.hp or 10,
                "ac": character.ac or 10,
                "equipment": getattr(character, 'equipment', '') or '',
            }
            session.set_selected_character(char_data)
            await websocket.send_json({
                "type": "system",
                "content": f"已选择角色: {character.name}，角色信息已注入 AI 上下文"
            })
    finally:
        db.close()


async def handle_save_game(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    message_data: dict,
    session: ChatSession
):
    """处理存档 —— P0-2: 保存完整游戏快照"""
    save_name = message_data.get("content", f"存档 {datetime.utcnow().strftime('%m-%d %H:%M')}")

    from database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = session.get_game_snapshot()
        save = Save(
            campaign_id=campaign_id,
            name=save_name,
            description=f"第 {snapshot.get('session_number', 1)} 章，{snapshot.get('messages_count', 0)} 条消息",
            snapshot=snapshot
        )
        db.add(save)
        db.commit()
        db.refresh(save)

        await websocket.send_json({
            "type": "save_created",
            "content": f"存档成功: {save_name}",
            "save": {
                "id": save.id,
                "name": save.name,
                "snapshot": save.snapshot,
                "created_at": str(save.created_at)
            }
        })
    except Exception as e:
        logger.error(f"存档失败: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"存档失败: {str(e)}"
        })
    finally:
        db.close()


async def handle_branch_create(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    message_data: dict,
    session: ChatSession
):
    """创建对话分支 —— P0-4"""
    branch_name = message_data.get("content", f"分支 {datetime.utcnow().strftime('%H:%M')}")
    parent_message_index = len(session.messages) - 1  # Fork from last message

    from database import SessionLocal
    db = SessionLocal()
    try:
        # 创建分支记录
        parent_msg_id = None
        if parent_message_index >= 0 and parent_message_index < len(session.messages):
            # 尝试获取对应的 SessionLog ID
            from models.save import SessionLog
            all_logs = db.query(SessionLog).filter(
                SessionLog.campaign_id == campaign_id
            ).order_by(SessionLog.id).all()
            if parent_message_index < len(all_logs):
                parent_msg_id = all_logs[parent_message_index].id

        branch = ChatBranch(
            campaign_id=campaign_id,
            parent_message_id=parent_msg_id,
            name=branch_name,
            is_active=True
        )
        db.add(branch)
        db.commit()
        db.refresh(branch)

        # 在会话中创建分支
        session.create_branch(branch.id, parent_message_index)
        session.switch_to_branch(branch.id)

        # 停用其他分支
        db.query(ChatBranch).filter(
            ChatBranch.campaign_id == campaign_id,
            ChatBranch.id != branch.id
        ).update({"is_active": False})
        db.commit()

        # 通知前端
        await websocket.send_json({
            "type": "branch_created",
            "content": f"已创建分支: {branch_name}",
            "branch": {"id": branch.id, "name": branch.name, "is_active": True, "created_at": str(branch.created_at)}
        })

        # 重新发送当前分支的消息
        for msg in session.messages:
            await websocket.send_json({
                "type": "kp_response" if msg.role == "kp" else "player_message",
                "role": msg.role,
                "content": msg.content
            })

        # 发送分支列表
        await _broadcast_branch_list(websocket, campaign_id, db)

    except Exception as e:
        logger.error(f"创建分支失败: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"创建分支失败: {str(e)}"
        })
    finally:
        db.close()


async def handle_branch_switch(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    message_data: dict,
    session: ChatSession
):
    """切换对话分支 —— P0-4"""
    branch_id = message_data.get("branch_id")  # None = 主线

    from database import SessionLocal
    db = SessionLocal()
    try:
        # 保存当前分支消息到数据库
        current_bid = session.current_branch_id
        # (消息在 switch_to_branch 中已保存到 branch_messages)

        # 切换到目标分支
        session.switch_to_branch(branch_id)

        # 更新激活状态
        db.query(ChatBranch).filter(
            ChatBranch.campaign_id == campaign_id
        ).update({"is_active": False})
        if branch_id:
            db.query(ChatBranch).filter(ChatBranch.id == branch_id).update({"is_active": True})
        db.commit()

        # 通知前端
        branch_name = "主线"
        if branch_id:
            branch = db.query(ChatBranch).filter(ChatBranch.id == branch_id).first()
            branch_name = branch.name if branch else f"分支 {branch_id}"

        # 清空前端消息
        await websocket.send_json({
            "type": "history_clear",
            "content": ""
        })

        # 发送切换后的消息
        for msg in session.messages:
            await websocket.send_json({
                "type": "kp_response" if msg.role == "kp" else "player_message",
                "role": msg.role,
                "content": msg.content
            })

        await websocket.send_json({
            "type": "branch_switched",
            "content": f"已切换到: {branch_name}",
            "branch_id": branch_id
        })

        await _broadcast_branch_list(websocket, campaign_id, db)

    except Exception as e:
        logger.error(f"切换分支失败: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"切换分支失败: {str(e)}"
        })
    finally:
        db.close()


async def handle_branch_list(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    session: ChatSession
):
    """获取分支列表 —— P0-4"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        await _broadcast_branch_list(websocket, campaign_id, db)
    finally:
        db.close()


async def _broadcast_branch_list(websocket: WebSocket, campaign_id: int, db):
    """广播分支列表"""
    branches = db.query(ChatBranch).filter(
        ChatBranch.campaign_id == campaign_id
    ).order_by(ChatBranch.created_at).all()

    branch_list = [
        {"id": b.id, "name": b.name, "is_active": b.is_active, "created_at": str(b.created_at)}
        for b in branches
    ]

    # 添加主线
    branch_list.insert(0, {"id": 0, "name": "主线", "is_active": True, "created_at": ""})

    await websocket.send_json({
        "type": "branch_list",
        "branches": branch_list
    })


async def handle_player_message(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    content: str,
    session: ChatSession
):
    """处理玩家消息"""
    # 检查是否是投骰命令
    if content.startswith("/roll ") or content.startswith("/r "):
        dice_str = content[5:] if content.startswith("/roll ") else content[3:]
        dice_result = parse_dice_command(dice_str)
        if dice_result:
            # 广播投骰结果
            dice_msg = format_dice_result(dice_result, "玩家投骰")
            await manager.broadcast(campaign_id, {
                "type": "dice_result",
                "role": "player",
                "content": dice_msg,
                "dice_type": dice_result.dice_type,
                "rolls": dice_result.rolls,
                "modifier": dice_result.modifier,
                "total": dice_result.total,
                "success": dice_result.success
            })

            # 记录消息
            session.add_message("player", content, dice_msg)
            return

    # 广播玩家消息
    await manager.broadcast(campaign_id, {
        "type": "player_message",
        "role": "player",
        "content": content,
        "username": user.username
    })

    # 记录消息
    session.add_message("player", content)

    # 调用 AI 获取响应
    await get_ai_response(campaign_id, session)


async def get_ai_response(campaign_id: int, session: ChatSession):
    """获取 AI KP 响应"""
    if not session.ai_config_id:
        await manager.broadcast(campaign_id, {
            "type": "system",
            "content": "未配置 AI，无法获取响应"
        })
        return

    # 获取 AI 配置
    from database import SessionLocal
    db = SessionLocal()
    try:
        ai_config = db.query(AIConfig).filter(AIConfig.id == session.ai_config_id).first()
        if not ai_config:
            await manager.broadcast(campaign_id, {
                "type": "system",
                "content": "AI 配置不存在"
            })
            return

        # 构建消息（限制历史消息数量避免请求过大）
        messages = [{"role": "system", "content": session.get_full_system_prompt()}]
        messages.extend(session.get_messages_for_ai(max_history=50))

        thinking_id = str(uuid.uuid4())

        # 发送思考中状态
        await manager.broadcast(campaign_id, {
            "type": "kp_thinking",
            "id": thinking_id,
            "content": "KP 正在思考..."
        })

        # 调用 AI (流式)
        try:
            logger.info(f"开始调用 AI: provider={ai_config.provider.value}, model={ai_config.model_name}, messages_count={len(messages)}")
            logger.debug(f"发送的消息: {messages}")

            full_response = ""
            chunk_count = 0
            async for chunk in AIGateway.chat_stream(
                provider_name=ai_config.provider.value.lower(),
                messages=messages,
                model=ai_config.model_name,
                api_key=ai_config.api_key,
                base_url=ai_config.base_url
            ):
                chunk_count += 1
                full_response += chunk
                if chunk_count <= 5:  # 只记录前5个chunk避免日志太多
                    logger.debug(f"收到chunk {chunk_count}: {repr(chunk)}")
                # 发送增量更新
                await manager.broadcast(campaign_id, {
                    "type": "kp_thinking_chunk",
                    "id": thinking_id,
                    "content": chunk
                })

            logger.info(f"AI响应完成: chunk_count={chunk_count}, full_response长度={len(full_response)}, 前100字符: {repr(full_response[:100])}")

            # 解析角色状态变化
            cleaned_response, char_updates = ChatSession.parse_character_updates(full_response)
            if char_updates:
                logger.info(f"检测到角色状态变化: {char_updates}")
                # 更新数据库中的角色
                character = db.query(Character).filter(
                    Character.user_id == db.query(Campaign).get(campaign_id).user_id
                ).first()
                if character:
                    _apply_character_updates(character, char_updates, session, db)
                # 广播角色状态更新到前端
                await manager.broadcast(campaign_id, {
                    "type": "character_update",
                    "role": "system",
                    "content": "角色状态已更新",
                    "updates": char_updates,
                    "stats": session.game_state.character_stats
                })

            # 广播 KP 响应（使用清理后的文本）
            await manager.broadcast(campaign_id, {
                "type": "kp_response",
                "thinking_id": thinking_id,
                "role": "kp",
                "content": cleaned_response
            })

            # 记录消息（存清理后的文本）
            session.add_message("kp", cleaned_response)

            # 保存到数据库
            log = SessionLog(
                campaign_id=campaign_id,
                session_number=session.game_state.session_number,
                branch_id=session.current_branch_id,
                role="kp",
                content=cleaned_response
            )
            db.add(log)
            db.commit()

        except Exception as e:
            logger.error(f"AI 调用失败: {type(e).__name__}: {str(e)}")
            await manager.broadcast(campaign_id, {
                "type": "error",
                "content": f"AI 调用失败: {type(e).__name__}: {str(e)}"
            })

    finally:
        db.close()


def _apply_character_updates(character, updates: Dict[str, int], session: ChatSession, db):
    """将 CHAR_UPDATE 变化应用到角色数据库和会话缓存"""
    stat_fields = {"STR", "DEX", "CON", "INT", "WIS", "CHA"}

    for field, delta in updates.items():
        if field == "hp":
            character.hp = max(0, (character.hp or 0) + delta)
        elif field == "ac":
            character.ac = max(0, (character.ac or 10) + delta)
        elif field == "level":
            character.level = max(1, (character.level or 1) + delta)
        elif field in stat_fields:
            attrs = dict(character.attributes or {})
            attrs[field] = max(1, min(30, attrs.get(field, 10) + delta))
            character.attributes = attrs

    db.commit()
    db.refresh(character)

    # 更新会话缓存
    session.set_character_stats(
        character_name=character.name,
        hp=character.hp or 0,
        ac=character.ac or 10,
        level=character.level or 1,
        attributes=character.attributes or {},
    )


async def handle_roll_command(websocket: WebSocket, campaign_id: int, dice_str: str):
    """处理投骰命令"""
    dice_result = parse_dice_command(dice_str)
    if dice_result:
        dice_msg = format_dice_result(dice_result)
        await manager.broadcast(campaign_id, {
            "type": "dice_result",
            "role": "system",
            "content": dice_msg,
            "dice_type": dice_result.dice_type,
            "rolls": dice_result.rolls,
            "modifier": dice_result.modifier,
            "total": dice_result.total,
            "success": dice_result.success
        })
    else:
        await websocket.send_json({
            "type": "error",
            "content": f"无法解析骰子命令: {dice_str}"
        })


async def handle_load_save(websocket: WebSocket, campaign_id: int, user: User, save_id: int):
    """处理加载存档 —— P0-2: 恢复完整游戏状态"""
    from database import SessionLocal
    from models.save import Save

    db = SessionLocal()
    try:
        save = db.query(Save).filter(Save.id == save_id).first()
        if not save or save.campaign_id != campaign_id:
            await websocket.send_json({
                "type": "error",
                "content": "存档不存在"
            })
            return

        # 加载状态
        session = ChatSessionManager.get_or_create_session(campaign_id)
        session.load_from_snapshot(save.snapshot)

        # 从数据库加载消息历史
        session.load_messages_from_db(campaign_id, db)

        # 标记为已生成开场（从存档加载了消息）
        session.story_generated = True

        # 发送清空消息
        await websocket.send_json({
            "type": "history_clear",
            "content": ""
        })

        # 广播加载的存档消息给前端
        for msg in session.messages:
            await websocket.send_json({
                "type": "kp_response" if msg.role == "kp" else "player_message",
                "role": msg.role,
                "content": msg.content
            })

        # 广播完整的加载信息，包含角色数据和场景
        await websocket.send_json({
            "type": "save_loaded",
            "content": f"已加载存档: {save.name}",
            "snapshot": save.snapshot,
            "scene": session.game_state.current_scene,
            "npcs": session.game_state.npcs,
            "locations": session.game_state.locations,
            "selected_character": session.game_state.selected_character,
            "character_stats": session.game_state.character_stats
        })

    finally:
        db.close()
