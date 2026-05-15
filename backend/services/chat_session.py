"""
Chat Session Service - 管理聊天会话和上下文
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json
import re


@dataclass
class Message:
    """聊天消息"""
    role: str  # 'player', 'kp', 'npc', 'ai_companion', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    dice_result: Optional[str] = None  # 投骰结果


@dataclass
class GameState:
    """游戏状态"""
    campaign_id: int
    session_number: int = 1
    current_scene: str = ""
    player_character_id: Optional[int] = None
    player_name: str = "Player"
    character_name: str = ""
    character_stats: Dict[str, int] = field(default_factory=dict)
    selected_character: Optional[Dict] = None  # 完整角色数据
    # 其他状态信息
    npcs: List[Dict] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)


class ChatSession:
    """单个战役的聊天会话"""

    def __init__(self, campaign_id: int):
        self.campaign_id = campaign_id
        self.messages: List[Message] = []
        self.game_state = GameState(campaign_id=campaign_id)
        self.ai_config_id: Optional[int] = None
        self.system_prompt: Optional[str] = None
        self.story_generated: bool = False  # 标记开场故事是否已生成
        # 分支对话
        self.current_branch_id: Optional[int] = None  # None = 主线
        self.branch_messages: Dict[int, List[Message]] = {}  # branch_id -> messages
        self.branch_parent_context: Dict[int, List[Message]] = {}  # branch_id -> parent context messages

    def add_message(self, role: str, content: str, dice_result: str = None) -> Message:
        """添加消息"""
        msg = Message(role=role, content=content, dice_result=dice_result)
        self.messages.append(msg)
        return msg

    def get_messages_for_ai(self, max_history: int = 50) -> List[Dict[str, str]]:
        """获取发送给 AI 的消息格式"""
        history = self.messages[-max_history:] if max_history > 0 else self.messages

        result = []
        for msg in history:
            # DeepSeek 只接受 system/user/assistant 角色
            # 映射规则: kp->assistant, player->user
            role = msg.role
            if role == "kp":
                role = "assistant"
            elif role == "player":
                role = "user"
            result.append({
                "role": role,
                "content": msg.content
            })
        return result

    def set_system_prompt(self, system_prompt: str):
        """设置系统提示词"""
        self.system_prompt = system_prompt

    def set_character_stats(self, character_name: str, hp: int, ac: int, level: int,
                            attributes: Dict[str, int], player_name: str = ""):
        """设置当前角色数据，用于状态追踪"""
        self.game_state.character_name = character_name
        self.game_state.player_name = player_name or self.game_state.player_name
        self.game_state.character_stats = {
            "hp": hp,
            "ac": ac,
            "level": level,
            "STR": attributes.get("STR", 10),
            "DEX": attributes.get("DEX", 10),
            "CON": attributes.get("CON", 10),
            "INT": attributes.get("INT", 10),
            "WIS": attributes.get("WIS", 10),
            "CHA": attributes.get("CHA", 10),
        }

    def set_selected_character(self, character_data: dict):
        """设置当前选中的完整角色数据，注入 AI 上下文"""
        self.game_state.selected_character = character_data
        self.game_state.player_character_id = character_data.get("id")
        # 同步更新角色状态缓存
        self.set_character_stats(
            character_name=character_data.get("name", ""),
            hp=character_data.get("hp", 10),
            ac=character_data.get("ac", 10),
            level=character_data.get("level", 1),
            attributes=character_data.get("attributes", {}),
            player_name=character_data.get("player_name", ""),
        )

    def get_full_system_prompt(self) -> str:
        """获取完整的系统提示词"""
        base_prompt = self.system_prompt or ""

        # 角色完整信息
        char_info_text = ""
        if self.game_state.selected_character:
            char = self.game_state.selected_character
            personality = char.get("personality", {}) or {}
            char_info_text = f"""
【当前玩家角色完整信息】
姓名: {char.get('name', '未知')} | 种族: {char.get('race', '未知')} | 职业: {char.get('character_class', '未知')} | 等级: {char.get('level', 1)}
背景故事: {char.get('backstory', '无')}
性格特征: {chr(10).join(f'  - {k}: {v}' for k, v in personality.items()) if personality else '  未设定'}
技能: {', '.join(char.get('skills', [])) if char.get('skills') else '无'}
装备: {char.get('equipment', '无')}
"""

        stats = self.game_state.character_stats
        stats_text = ""
        if stats:
            stats_text = f"""
【当前角色状态】
- 名称: {self.game_state.character_name}
- HP: {stats.get('hp', '?')} | AC: {stats.get('ac', '?')} | 等级: {stats.get('level', '?')}
- 属性: 力量{stats.get('STR','?')} 敏捷{stats.get('DEX','?')} 体质{stats.get('CON','?')} 智力{stats.get('INT','?')} 感知{stats.get('WIS','?')} 魅力{stats.get('CHA','?')}

【状态变化规则 - 非常重要】
当游戏中角色受到伤害、治疗、属性变化或任何状态改变时，你必须在回复末尾用以下格式标记：
[CHAR_UPDATE: hp=-5]  表示HP减少5
[CHAR_UPDATE: hp=+3]  表示HP恢复3
[CHAR_UPDATE: STR=+1]  表示力量+1
[CHAR_UPDATE: ac=-2]  表示护甲-2
可用的字段: hp, ac, level, STR, DEX, CON, INT, WIS, CHA
多个变化可以同时标记，例如: [CHAR_UPDATE: hp=-8][CHAR_UPDATE: STR=-1]
数字前必须有+或-号表示增减。
"""

        player_info = f"""
当前玩家: {self.game_state.character_name} ({self.game_state.player_name})
当前场景: {self.game_state.current_scene or "未设定"}
会话次数: 第 {self.game_state.session_number} 章

请作为 TRPG 的 KP/主持人，引导玩家进行冒险。
保持剧情连贯性，适当设置悬念和挑战。
当玩家请求投骰时，请使用 /roll 命令。

【回复格式要求 - 必须严格遵守】
你的每次回复必须使用以下标记来组织内容，让玩家能清晰分辨不同类型的信息：

[DESC]环境描写、场景氛围、叙事性描述[/DESC]
[ACTION]玩家角色的行动结果、你做了什么、检定结果[/ACTION]
[NPC]NPC的行动、对话、反应[/NPC]
[EVENT]环境变化、突发事件、新线索出现[/EVENT]
[STATUS]角色状态变化提醒（HP增减、属性变化、获得物品等）[/STATUS]

格式规则：
1. 每个段落必须用对应的标记包裹
2. 可以省略不需要的标记（如本轮没有NPC动作就不写[NPC]）
3. 标记必须是英文大写，成对出现（开始和结束）
4. 多个同类内容可以放在同一个标记块内
5. 示例回复格式：
[DESC]幽暗的走廊尽头传来低沉的呼吸声，墙上的火把摇曳不定...[/DESC]
[ACTION]你小心翼翼地推开房门，敏捷检定成功(DC 15, 掷出18)。房间里堆满了古老的书籍。[/ACTION]
[STATUS]你的理智值因目睹不可名状之物而动摇。[/STATUS]

【行动建议】
在回复的最末尾，根据当前剧情给出3-4个具体、贴合场景的行动建议，格式为：
[SUGGESTIONS: 建议1 | 建议2 | 建议3]
建议要具体且有针对性，不要泛泛而谈。例如：
[SUGGESTIONS: 调查书桌上的笔记 | 与酒馆老板打听消息 | 悄悄尾随可疑的商人]
"""
        return base_prompt + char_info_text + stats_text + player_info if base_prompt else char_info_text + stats_text + player_info

    @staticmethod
    def parse_suggestions(text: str) -> tuple[str, list[str]]:
        """从 AI 响应中提取行动建议，返回 (清理后文本, 建议列表)"""
        pattern = r'\[SUGGESTIONS:\s*([^\]]+)\]'
        suggestions: list[str] = []
        match = re.search(pattern, text)
        if match:
            raw = match.group(1).strip()
            suggestions = [s.strip() for s in raw.split('|') if s.strip()]
        cleaned = re.sub(pattern, '', text).strip()
        return cleaned, suggestions

    @staticmethod
    def parse_character_updates(text: str) -> tuple[str, Dict[str, int]]:
        """从 AI 响应文本中提取角色状态变化，返回 (清理后文本, 变化字典)

        解析 [CHAR_UPDATE: field=+delta] 或 [CHAR_UPDATE: field=-delta] 格式。
        delta 必须是带正负号的整数。
        """
        pattern = r'\[CHAR_UPDATE:\s*(\w+)\s*=\s*([+-]\d+)\]'
        updates: Dict[str, int] = {}
        cleaned = text

        for match in re.finditer(pattern, text):
            field = match.group(1)
            delta_str = match.group(2)
            try:
                delta = int(delta_str)
            except ValueError:
                continue
            if field in updates:
                updates[field] += delta
            else:
                updates[field] = delta

        cleaned = re.sub(pattern, '', text).strip()
        # 清理多余空行
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned, updates

    def get_game_snapshot(self) -> Dict[str, Any]:
        """获取游戏快照，用于存档"""
        return {
            "campaign_id": self.campaign_id,
            "session_number": self.game_state.session_number,
            "current_scene": self.game_state.current_scene,
            "player_character_id": self.game_state.player_character_id,
            "player_name": self.game_state.player_name,
            "character_name": self.game_state.character_name,
            "character_stats": self.game_state.character_stats,
            "selected_character": self.game_state.selected_character,
            "npcs": self.game_state.npcs,
            "locations": self.game_state.locations,
            "messages_count": len(self.messages)
        }

    def load_from_snapshot(self, snapshot: Dict[str, Any]):
        """从快照加载游戏状态"""
        self.game_state.session_number = snapshot.get("session_number", 1)
        self.game_state.current_scene = snapshot.get("current_scene", "")
        self.game_state.player_character_id = snapshot.get("player_character_id")
        self.game_state.player_name = snapshot.get("player_name", "Player")
        self.game_state.character_name = snapshot.get("character_name", "")
        self.game_state.character_stats = snapshot.get("character_stats", {})
        self.game_state.selected_character = snapshot.get("selected_character")
        self.game_state.npcs = snapshot.get("npcs", [])
        self.game_state.locations = snapshot.get("locations", [])

    def load_messages_from_db(self, campaign_id: int, db):
        """从数据库加载消息历史"""
        from models.save import SessionLog
        logs = db.query(SessionLog).filter(
            SessionLog.campaign_id == campaign_id
        ).order_by(SessionLog.id).all()

        self.messages.clear()
        for log in logs:
            self.messages.append(Message(
                role=log.role,
                content=log.content
            ))

        # 如果有消息，标记为已生成开场
        if self.messages:
            self.story_generated = True

    # ── 分支对话管理 ──

    def create_branch(self, branch_id: int, parent_message_index: int) -> List[Message]:
        """创建新分支，从指定消息处 fork

        parent_message_index: 分支起点在 main messages 中的索引
        返回: 分支的初始消息列表（fork 点之前的消息副本）
        """
        parent_messages = self.messages[:parent_message_index + 1]
        self.branch_parent_context[branch_id] = list(parent_messages)
        branch_msgs = list(parent_messages)
        self.branch_messages[branch_id] = branch_msgs
        return branch_msgs

    def switch_to_branch(self, branch_id: Optional[int]):
        """切换到指定分支（None = 主线）"""
        # 保存当前分支的消息
        if self.current_branch_id is not None:
            self.branch_messages[self.current_branch_id] = list(self.messages)
        else:
            # 当前是主线，保存到 self.messages（已经在 self.messages 中）
            pass

        # 加载目标分支的消息
        if branch_id is not None and branch_id in self.branch_messages:
            self.messages = self.branch_messages[branch_id]
        elif branch_id is None:
            # 切回主线 — messages 保持在当前位置，无需特殊处理
            pass

        self.current_branch_id = branch_id

    def get_messages_for_ai(self, max_history: int = 50) -> List[Dict[str, str]]:
        """获取发送给 AI 的消息格式（包含分支上下文）"""
        history = self.messages[-max_history:] if max_history > 0 else self.messages

        # 如果在分支中，前置注入主线上下文摘要
        result = []
        if self.current_branch_id is not None:
            parent_ctx = self.branch_parent_context.get(self.current_branch_id, [])
            if parent_ctx:
                last_parent = parent_ctx[-1]
                result.append({
                    "role": "system",
                    "content": f"[分支上下文] 此对话从主线分叉，分叉点之前的最后一条消息: {last_parent.content[:200]}"
                })

        for msg in history:
            role = msg.role
            if role == "kp":
                role = "assistant"
            elif role == "player":
                role = "user"
            result.append({
                "role": role,
                "content": msg.content
            })
        return result

    def merge_branch_summary(self, branch_id: int, summary: str):
        """将分支摘要合并回主线上下文"""
        if branch_id in self.branch_messages:
            self.add_message("system", f"[分支摘要: {branch_id}] {summary}")
            # 清理分支数据
            del self.branch_messages[branch_id]
            if branch_id in self.branch_parent_context:
                del self.branch_parent_context[branch_id]


class ChatSessionManager:
    """管理所有活跃的聊天会话"""

    _sessions: Dict[int, ChatSession] = {}

    @classmethod
    def get_or_create_session(cls, campaign_id: int) -> ChatSession:
        """获取或创建会话"""
        if campaign_id not in cls._sessions:
            cls._sessions[campaign_id] = ChatSession(campaign_id)
        return cls._sessions[campaign_id]

    @classmethod
    def remove_session(cls, campaign_id: int):
        """移除会话"""
        if campaign_id in cls._sessions:
            del cls._sessions[campaign_id]

    @classmethod
    def get_session(cls, campaign_id: int) -> Optional[ChatSession]:
        """获取会话（如果存在）"""
        return cls._sessions.get(campaign_id)
