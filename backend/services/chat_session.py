"""
Chat Session Service - 管理聊天会话和上下文
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import json


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

    def get_full_system_prompt(self) -> str:
        """获取完整的系统提示词"""
        base_prompt = self.system_prompt or ""

        # 添加玩家信息
        player_info = f"""
当前玩家: {self.game_state.character_name} ({self.game_state.player_name})
当前场景: {self.game_state.current_scene or "未设定"}
会话次数: 第 {self.game_state.session_number} 章

请作为 D&D 5e 的 KP/主持人，引导玩家进行冒险。
保持剧情连贯性，适当设置悬念和挑战。
当玩家请求投骰时，请使用 /roll 命令。
"""
        return base_prompt + player_info if base_prompt else player_info

    def get_game_snapshot(self) -> Dict[str, Any]:
        """获取游戏快照，用于存档"""
        return {
            "campaign_id": self.campaign_id,
            "session_number": self.game_state.session_number,
            "current_scene": self.game_state.current_scene,
            "player_character_id": self.game_state.player_character_id,
            "player_name": self.game_state.player_name,
            "character_name": self.game_state.character_name,
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
