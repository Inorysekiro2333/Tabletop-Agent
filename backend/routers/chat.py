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
from models.save import Save, SessionLog
from models.chat_branch import ChatBranch
from utils.security import get_current_user, verify_token
from services.ai_gateway import AIGateway
from services.chat_session import ChatSessionManager, ChatSession
from services.dice import parse_dice_command, format_dice_result, parse_action_command
from services.dice import resolve_attack, resolve_skill_check, resolve_saving_throw, get_ability_modifier

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

        # 更新最近游玩时间
        campaign.last_played_at = datetime.utcnow()
        db.commit()

        # 获取或创建会话，尝试从 Redis 恢复
        session = ChatSessionManager.get_or_create_session(campaign_id)
        redis_session = await ChatSessionManager.restore_from_redis(campaign_id)
        if redis_session and redis_session.story_generated:
            session = redis_session
            logger.info(f"从 Redis 恢复了会话: campaign_id={campaign_id}")

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

        # 加载战役绑定的角色数据到会话（状态追踪 + AI 上下文注入）
        character = None
        if campaign.character_id:
            character = db.query(Character).filter(
                Character.id == campaign.character_id,
                Character.user_id == user.id
            ).first()
        if not character:
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
                "equipment": character.equipment or [],
                "relationships": character.relationships or [],
                "faction": character.faction or "",
                "goals": character.goals or [],
                "ideals": character.ideals or [],
                "flaws": character.flaws or [],
                "personal_traits": character.personal_traits or [],
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
        "timestamp": str(campaign.created_at) if campaign.created_at else ""
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
            elif msg_type == "branch_message":
                await handle_branch_message(websocket, campaign_id, user, content, session)

    except WebSocketDisconnect:
        await ChatSessionManager.save_to_redis(campaign_id)
        manager.disconnect(websocket, campaign_id)
    except Exception as e:
        await ChatSessionManager.save_to_redis(campaign_id)
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
                "equipment": character.equipment or [],
                "relationships": character.relationships or [],
                "faction": character.faction or "",
                "goals": character.goals or [],
                "ideals": character.ideals or [],
                "flaws": character.flaws or [],
                "personal_traits": character.personal_traits or [],
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
    """处理存档 —— 保存完整游戏快照，生成丰富摘要"""
    save_name = message_data.get("content", f"存档 {datetime.utcnow().strftime('%m-%d %H:%M')}")

    from database import SessionLocal
    db = SessionLocal()
    try:
        snapshot = session.get_game_snapshot()

        # 生成丰富的存档摘要
        desc_parts = [f"第 {snapshot.get('session_number', 1)} 章"]
        scene = snapshot.get("current_scene", "")
        if scene:
            desc_parts.append(f"场景: {scene[:30]}")
        char_name = snapshot.get("character_name", "")
        if char_name:
            desc_parts.append(f"角色: {char_name}")
        quests = snapshot.get("quests", [])
        if quests:
            active_quests = [q.get("name", str(q)) for q in quests if isinstance(q, dict) and q.get("status") != "完成"]
            if active_quests:
                desc_parts.append(f"任务: {', '.join(active_quests[:2])}")
        combat = snapshot.get("combat_state", {})
        if combat and combat.get("is_active"):
            desc_parts.append(f"战斗中 (第{combat.get('round', 1)}轮)")
        npcs = snapshot.get("npcs", [])
        if npcs:
            desc_parts.append(f"NPC: {len(npcs)}人")
        desc_parts.append(f"{snapshot.get('messages_count', 0)}条消息")
        description = " | ".join(desc_parts)

        save = Save(
            campaign_id=campaign_id,
            name=save_name,
            description=description,
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
    """创建对话分支 —— 压缩当前上下文为 JSON 快照存入 DB，供分支 AI 引用"""
    branch_name = message_data.get("content", f"分支 {datetime.utcnow().strftime('%H:%M')}")
    frontend_messages = message_data.get("messages", [])  # 前端传来的当前对话

    from database import SessionLocal
    db = SessionLocal()
    try:
        fork_index = len(session.messages) - 1
        # 生成完整上下文快照（传入前端消息以弥补预设开场白不在后端 session 的问题）
        context_snapshot = session.build_context_snapshot(fork_index, frontend_messages)

        branch = ChatBranch(
            campaign_id=campaign_id,
            parent_message_id=len(session.messages),
            name=branch_name,
            is_active=True,
            context_snapshot=context_snapshot,
        )
        db.add(branch)
        db.commit()
        db.refresh(branch)

        # Store branch info in session for context isolation
        session.create_branch(branch.id, fork_index)

        await websocket.send_json({
            "type": "branch_created",
            "content": "分支对话已创建，上下文快照已保存",
            "branch": {"id": branch.id, "name": branch.name}
        })

    except Exception as e:
        logger.error(f"创建分支失败: {e}")
        await websocket.send_json({
            "type": "error",
            "content": f"创建分支失败: {str(e)}"
        })
    finally:
        db.close()


async def handle_branch_message(
    websocket: WebSocket,
    campaign_id: int,
    user: User,
    content: str,
    session: ChatSession
):
    """处理分支对话消息 —— 独立于主线，但带主线记忆，流式输出，轻松闲聊人设"""
    if not session.ai_config_id:
        await websocket.send_json({
            "type": "branch_system",
            "content": "未配置 AI"
        })
        return

    from database import SessionLocal
    db = SessionLocal()
    try:
        ai_config = db.query(AIConfig).filter(AIConfig.id == session.ai_config_id).first()
        if not ai_config:
            return

        # ── 加载分支上下文快照（存于 DB 的 JSON，创建分支时生成） ──
        branch_id = session.current_branch_id
        snapshot = None
        if branch_id:
            branch_record = db.query(ChatBranch).filter(ChatBranch.id == branch_id).first()
            if branch_record and branch_record.context_snapshot:
                snapshot = branch_record.context_snapshot

        # 从快照构建上下文；无快照时回退到当前 session 状态
        ctx_world_setting = ""
        if snapshot:
            ctx_char = snapshot.get("character", {})
            ctx_world = snapshot.get("world", {})
            ctx_exchanges = snapshot.get("recent_exchanges", [])
            ctx_world_setting = snapshot.get("world_setting", "")
            char_name = ctx_char.get("name", "玩家")
            char_stats = ctx_char.get("attributes", {})
            char_stats["hp"] = ctx_char.get("hp", 10)
            char_stats["ac"] = ctx_char.get("ac", 10)
            char_stats["level"] = ctx_char.get("level", 1)
        else:
            ctx_char = session.game_state.selected_character or {}
            ctx_world = {
                "current_scene": session.game_state.current_scene or "",
                "npcs": session.game_state.npcs or [],
                "quests": session.game_state.quests or [],
                "locations": session.game_state.locations or [],
            }
            ctx_exchanges = []
            char_name = session.game_state.character_name or "玩家"
            char_stats = session.game_state.character_stats

        stats_summary = f"HP:{char_stats.get('hp','?')} AC:{char_stats.get('ac','?')} LV:{char_stats.get('level','?')}" if char_stats else ""

        # ── 从快照提取角色信息 ──
        equipment = ctx_char.get("equipment", []) or []
        eq_text = "、".join(equipment) if equipment else "无"
        skills_text = "、".join(ctx_char.get("skills", []) or []) if ctx_char.get("skills") else "无"
        backstory = ctx_char.get("backstory", "") or ""
        personality = ctx_char.get("personality", {}) or {}
        personality_text = "；".join([f"{k}: {v}" for k, v in personality.items()]) if personality else "无"
        faction = ctx_char.get("faction", "") or ""
        goals_list = ctx_char.get("goals", []) or []
        goals_text = "；".join([g.get("name", str(g)) if isinstance(g, dict) else str(g) for g in goals_list[:3]]) if goals_list else "无"
        relationships = ctx_char.get("relationships", []) or []
        rel_text = "；".join([f"{r.get('name','?')}({r.get('type','?')})" if isinstance(r, dict) else str(r) for r in relationships[:5]]) if relationships else "无"
        personal_traits = ctx_char.get("personal_traits", []) or []
        ideals = ctx_char.get("ideals", []) or []
        flaws = ctx_char.get("flaws", []) or []

        # ── 从快照提取世界状态 ──
        memory_parts = []
        current_scene = ctx_world.get("current_scene", "")
        if current_scene:
            memory_parts.append(f"当前场景: {current_scene}")

        npcs = ctx_world.get("npcs", []) or []
        if npcs:
            npc_lines = ["已登场的NPC:"]
            for npc in npcs[:5]:
                name = npc.get("name", "?") if isinstance(npc, dict) else str(npc)
                role = npc.get("role", "") if isinstance(npc, dict) else ""
                attitude = npc.get("attitude", "") if isinstance(npc, dict) else ""
                desc = npc.get("description", "") if isinstance(npc, dict) else ""
                npc_lines.append(f"  - {name}" + (f" ({role})" if role else "") + (f" [{attitude}]" if attitude else "") + (f": {desc}" if desc else ""))
            memory_parts.append("\n".join(npc_lines))

        quests = ctx_world.get("quests", []) or []
        if quests:
            quest_lines = ["当前任务:"]
            for q in quests[:3]:
                name = q.get("name", "?") if isinstance(q, dict) else str(q)
                status = q.get("status", "") if isinstance(q, dict) else ""
                quest_lines.append(f"  - {name}" + (f" [{status}]" if status else ""))
            memory_parts.append("\n".join(quest_lines))

        locations = ctx_world.get("locations", []) or []
        if locations:
            loc_lines = ["已知地点:"]
            for loc in locations[:3]:
                name = loc.get("name", "?") if isinstance(loc, dict) else str(loc)
                loc_lines.append(f"  - {name}")
            memory_parts.append("\n".join(loc_lines))

        # ── 世界设定（从 system_prompt 提取的背景设定） ──
        world_setting_text = ""
        if snapshot and ctx_world_setting:
            world_setting_text = f"【世界背景设定】\n{ctx_world_setting[:500]}"

        memory_text = ""
        if memory_parts:
            memory_text = "【世界信息 — 来自分支创建时的快照】\n" + "\n\n".join(memory_parts)
        if world_setting_text:
            memory_text = world_setting_text + "\n\n" + memory_text if memory_text else world_setting_text

        # ── 最近对话摘要（fork 点前的关键回合） ──
        recent_text = ""
        if ctx_exchanges:
            recent_text = "【分支创建前的最近对话】\n" + "\n".join([
                f"[{ex.get('role','?')}]: {ex.get('content','')[:200]}"
                for ex in ctx_exchanges[-6:]
            ])

        # ── 系统提示 ──
        branch_system_prompt = f"""你是 {char_name} 的冒险伙伴。你们正在一起冒险，现在私下聊几句。

【说话方式】
- 用"我"指自己，用"你"指 {char_name}，像朋友聊天一样
- 口语化、接地气，不要书面语，不要长篇大论
- 可以吐槽、出主意、分析局势、反问
- 每回合2-4句话就够

【{char_name} 的完整信息 — 来自上下文快照】
姓名: {ctx_char.get('name', char_name)}
种族/职业: {ctx_char.get('race', '未知')} {ctx_char.get('class', ctx_char.get('character_class', ''))} Lv.{ctx_char.get('level', 1)}
状态: {stats_summary}
背景: {backstory[:200] if backstory else '无'}
性格: {personality_text}
个人特质: {', '.join(personal_traits) if personal_traits else '无'}
理想/信念: {', '.join(ideals) if ideals else '无'}
性格缺陷: {', '.join(flaws) if flaws else '无'}
阵营: {faction or '无'}
背包物品: {eq_text}
技能: {skills_text}
人际关系: {rel_text}
当前目标: {goals_text}

{memory_text}

{recent_text}

【铁律 — 违反一条就会出戏】
1. 绝不编造 NPC、物品、地点或事件。只能引用上面快照中列出的
2. 玩家包里有什么就是什么，别凭空加东西
3. 对话摘要里写的就是已经发生的，别篡改
4. 不知道就说"我不清楚"，别瞎编
5. 别用 [DESC] [ACTION] 这些KP标记，你不是KP
6. 根据 {char_name} 的性格、特质和缺陷来回应，性格影响说话方式和态度

你就是 {char_name} 身边最可靠的搭档。上述快照是唯一的事实依据。"""

        # 构建 messages
        messages = [{"role": "system", "content": branch_system_prompt}]
        messages.append({"role": "user", "content": content})

        thinking_id = str(uuid.uuid4())

        # 发送思考中状态
        await websocket.send_json({
            "type": "branch_kp_thinking",
            "id": thinking_id,
            "content": "分支 KP 思考中..."
        })

        # 流式调用 AI
        full_response = ""
        async for chunk in AIGateway.chat_stream(
            provider_name=ai_config.provider.value.lower(),
            messages=messages,
            model=ai_config.model_name,
            api_key=ai_config.api_key,
            base_url=ai_config.base_url
        ):
            full_response += chunk
            await websocket.send_json({
                "type": "branch_kp_thinking_chunk",
                "id": thinking_id,
                "content": chunk
            })

        await websocket.send_json({
            "type": "branch_kp_response",
            "thinking_id": thinking_id,
            "role": "kp",
            "content": full_response
        })

    except Exception as e:
        logger.error(f"分支消息处理失败: {e}")
        await websocket.send_json({
            "type": "branch_system",
            "content": f"AI 响应失败: {str(e)}"
        })
    finally:
        db.close()


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
            session.add_message("player", content, dice_msg)
            return

    # 检查是否是动作/判定命令
    action = parse_action_command(content)
    if action:
        char_data = session.game_state.selected_character or {}
        action_type = action["action_type"]

        if action_type == "attack":
            # 构建防御者数据（从敌人列表找目标）
            target_name = action.get("target", "敌人")
            defender = {"name": target_name, "ac": 12, "hp": 20}
            for enemy in session.game_state.enemies:
                if enemy.get("name", "").lower() == target_name.lower():
                    defender = enemy
                    break

            atk_bonus = get_ability_modifier(char_data, "STR")
            result = resolve_attack(char_data, defender, atk_bonus,
                                    action.get("damage_dice", "1d6"))

            # 广播战斗结果
            await manager.broadcast(campaign_id, {
                "type": "dice_result",
                "role": "system",
                "content": result["description"],
                "rolls": [result["attack_roll"]],
                "total": result["attack_total"],
                "success": result["success"],
                "damage": result["damage"],
                "is_crit": result.get("is_crit", False),
                "is_fumble": result.get("is_fumble", False),
            })

            # 存储判定结果供 AI 叙事
            session.game_state.last_judgment = result
            session.add_message("player", content)
            await get_ai_response(campaign_id, session)
            return

        elif action_type == "skill_check":
            result = resolve_skill_check(char_data, action["skill"], action["dc"])
            await manager.broadcast(campaign_id, {
                "type": "dice_result",
                "role": "system",
                "content": result["description"],
                "rolls": [result["roll"]],
                "total": result["total"],
                "success": result["success"],
                "skill": action["skill"],
                "dc": action["dc"],
            })
            session.game_state.last_judgment = result
            session.add_message("player", content)
            await get_ai_response(campaign_id, session)
            return

        elif action_type == "cast":
            result = {
                "action_type": "cast",
                "spell": action["spell"],
                "description": f"施放 {action['spell']}",
                "success": True,
            }
            session.game_state.last_judgment = result
            session.add_message("player", content)
            await get_ai_response(campaign_id, session)
            return

        elif action_type == "use_item":
            result = {
                "action_type": "use_item",
                "item": action["item"],
                "description": f"使用 {action['item']}",
                "success": True,
            }
            session.game_state.last_judgment = result
            session.add_message("player", content)
            await get_ai_response(campaign_id, session)
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

        # 构建消息：记忆摘要 + 系统提示 + 精简历史
        messages = [{"role": "system", "content": session.get_memory_prompt()}]
        messages.append({"role": "system", "content": session.get_full_system_prompt()})

        # 注入当前判定结果（规则引擎输出）
        if session.game_state.last_judgment:
            j = session.game_state.last_judgment
            judgment_text = f"【当前回合判定结果】{j.get('description', '')} — 请根据此结果生成环境描述和NPC反应。"
            messages.append({"role": "system", "content": judgment_text})
            session.game_state.last_judgment = None  # 消费后清除

        messages.extend(session.get_messages_for_ai(max_history=20))

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

            # 解析行动建议
            cleaned_response, suggestions = ChatSession.parse_suggestions(full_response)
            # 解析角色状态变化
            cleaned_response, char_updates = ChatSession.parse_character_updates(cleaned_response)
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
                "content": cleaned_response,
                "suggestions": suggestions
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

    # 同步更新 selected_character 缓存，确保 AI 上下文与最新状态一致
    updated_char_data = {
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
        "equipment": character.equipment or [],
        "relationships": character.relationships or [],
        "faction": character.faction or "",
        "goals": character.goals or [],
        "ideals": character.ideals or [],
        "flaws": character.flaws or [],
        "personal_traits": character.personal_traits or [],
    }
    session.set_selected_character(updated_char_data)


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
    """处理加载存档 —— 恢复完整世界状态（场景/NPC/任务/战斗/分支）"""
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

        snapshot = save.snapshot

        # 加载完整状态
        session = ChatSessionManager.get_or_create_session(campaign_id)
        session.load_from_snapshot(snapshot)

        # 恢复分支上下文
        branch_id = snapshot.get("branch_id")
        if branch_id is not None:
            session.current_branch_id = branch_id

        # 从数据库加载消息历史
        session.load_messages_from_db(campaign_id, db)

        # 标记为已生成开场
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

        # 广播完整的世界状态（包含所有新字段）
        await websocket.send_json({
            "type": "save_loaded",
            "content": f"已加载存档: {save.name}",
            "snapshot": snapshot,
            "scene": session.game_state.current_scene,
            "npcs": session.game_state.npcs,
            "locations": session.game_state.locations,
            "quests": session.game_state.quests,
            "world_state": session.game_state.world_state,
            "combat_state": session.game_state.combat_state,
            "enemies": session.game_state.enemies,
            "turn_order": session.game_state.turn_order,
            "initiative": session.game_state.initiative,
            "relationship_map": session.game_state.relationship_map,
            "selected_character": session.game_state.selected_character,
            "character_stats": session.game_state.character_stats,
            "branch_id": session.current_branch_id,
        })

    finally:
        db.close()
