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
    # 结构化世界状态
    npcs: List[Dict] = field(default_factory=list)  # [{name, role, attitude, location, description, ac, hp}]
    locations: List[Dict] = field(default_factory=list)  # [{name, description, status, explored}]
    quests: List[Dict] = field(default_factory=list)  # [{name, description, status, objective}]
    world_state: Dict[str, Any] = field(default_factory=dict)  # e.g., {weather, pressure, faction_power}
    relationship_map: Dict[str, str] = field(default_factory=dict)  # NPC/角色间关系
    # 战斗状态
    combat_state: Dict = field(default_factory=dict)  # {is_active, round, turn_index}
    enemies: List[Dict] = field(default_factory=list)  # [{name, ac, hp, attacks}]
    turn_order: List[str] = field(default_factory=list)
    initiative: Dict[str, int] = field(default_factory=dict)
    # 当前判定结果（规则引擎输出，供 AI 叙事使用）
    last_judgment: Optional[Dict] = None


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

    def get_memory_prompt(self) -> str:
        """生成结构化记忆摘要，只保留最关键的 5-8 条信息"""
        gs = self.game_state
        blocks = []

        # NPC（最多3个重要NPC）
        if gs.npcs:
            npc_lines = []
            for npc in gs.npcs[:3]:
                name = npc.get("name", "?") if isinstance(npc, dict) else str(npc)
                role = npc.get("role", "") if isinstance(npc, dict) else ""
                attitude = npc.get("attitude", "") if isinstance(npc, dict) else ""
                npc_lines.append(f"  - {name}" + (f" ({role})" if role else "") + (f" [态度: {attitude}]" if attitude else ""))
            if npc_lines:
                blocks.append("【重要NPC】\n" + "\n".join(npc_lines))

        # 当前任务（最多3个）
        if gs.quests:
            quest_lines = []
            for q in gs.quests[:3]:
                name = q.get("name", "?") if isinstance(q, dict) else str(q)
                status = q.get("status", "") if isinstance(q, dict) else ""
                quest_lines.append(f"  - {name}" + (f" [{status}]" if status else ""))
            if quest_lines:
                blocks.append("【当前任务】\n" + "\n".join(quest_lines))

        # 当前地点
        if gs.current_scene:
            blocks.append(f"【当前场景】{gs.current_scene}")

        if gs.locations:
            loc_lines = []
            for loc in gs.locations[:3]:
                name = loc.get("name", "?") if isinstance(loc, dict) else str(loc)
                status = loc.get("status", "") if isinstance(loc, dict) else ""
                loc_lines.append(f"  - {name}" + (f" [{status}]" if status else ""))
            if loc_lines:
                blocks.append("【已知地点】\n" + "\n".join(loc_lines))

        # 关系网
        if gs.relationship_map:
            rel_lines = [f"  - {k}: {v}" for k, v in list(gs.relationship_map.items())[:5]]
            blocks.append("【关系网】\n" + "\n".join(rel_lines))

        # 世界状态
        if gs.world_state:
            ws_lines = [f"  - {k}: {v}" for k, v in list(gs.world_state.items())[:5]]
            blocks.append("【世界状态】\n" + "\n".join(ws_lines))

        # 战斗状态
        if gs.combat_state and gs.combat_state.get("is_active"):
            blocks.append(f"【战斗中】第{gs.combat_state.get('round', 1)}轮 | 敌人: {', '.join(e.get('name', '?') for e in gs.enemies[:5]) if gs.enemies else '无'}")

        # 角色摘要
        char_summary = self.get_character_summary()
        if char_summary and char_summary != "未选择角色":
            blocks.append(f"【当前角色】{char_summary}")

        if not blocks:
            return "暂无结构化记忆"

        return "【结构化记忆 — 当前世界状态】\n" + "\n\n".join(blocks)

    def get_character_summary(self) -> str:
        """生成角色简要摘要，用于记忆注入和存档预览"""
        char = self.game_state.selected_character
        if not char:
            return "未选择角色"

        stats = self.game_state.character_stats
        parts = [
            f"{char.get('name', '未知')}",
            f"{char.get('race', '')} {char.get('character_class', '')} Lv.{char.get('level', 1)}",
        ]
        if stats:
            parts.append(f"HP:{stats.get('hp','?')}/{char.get('hp','?')} AC:{stats.get('ac','?')}")
        faction = char.get("faction", "")
        if faction:
            parts.append(f"阵营: {faction}")
        goals = char.get("goals", []) or []
        if goals:
            goal_names = [g.get("name", str(g)) if isinstance(g, dict) else str(g) for g in goals[:3]]
            parts.append(f"目标: {', '.join(goal_names)}")
        return " | ".join(parts)

    def get_character_state_text(self) -> str:
        """生成角色当前状态文本"""
        stats = self.game_state.character_stats
        if not stats:
            return "角色状态未初始化"

        lines = [
            f"HP: {stats.get('hp', '?')} | AC: {stats.get('ac', '?')} | 等级: {stats.get('level', '?')}",
            f"力量:{stats.get('STR','?')} 敏捷:{stats.get('DEX','?')} 体质:{stats.get('CON','?')}",
            f"智力:{stats.get('INT','?')} 感知:{stats.get('WIS','?')} 魅力:{stats.get('CHA','?')}",
        ]
        return "\n".join(lines)

    def get_full_system_prompt(self) -> str:
        """获取完整的系统提示词"""
        base_prompt = self.system_prompt or ""

        # 角色完整信息
        char_info_text = ""
        if self.game_state.selected_character:
            char = self.game_state.selected_character
            personality = char.get("personality", {}) or {}
            relationships = char.get("relationships", []) or []
            goals = char.get("goals", []) or []
            faction = char.get("faction", "")
            ideals = char.get("ideals", []) or []
            flaws = char.get("flaws", []) or []
            personal_traits = char.get("personal_traits", []) or []
            equipment = char.get("equipment", []) or []

            # Build relationships text
            rel_text = ""
            if relationships:
                rel_lines = []
                for r in relationships:
                    if isinstance(r, dict):
                        rel_lines.append(f"  - {r.get('name', '?')} ({r.get('type', '?')}): {r.get('description', '')} [态度: {r.get('attitude', '?')}]")
                    else:
                        rel_lines.append(f"  - {r}")
                rel_text = "\n".join(rel_lines)

            # Build goals text
            goals_text = ""
            if goals:
                goals_lines = []
                for g in goals:
                    if isinstance(g, dict):
                        goals_lines.append(f"  - {g.get('name', '?')}: {g.get('description', '')} [{g.get('status', '进行中')}]")
                    else:
                        goals_lines.append(f"  - {g}")
                goals_text = "\n".join(goals_lines)

            # Build equipment text
            eq_text = ", ".join(equipment) if isinstance(equipment, list) else str(equipment)

            char_info_text = f"""
【当前玩家角色完整信息 — 这是"你"】
姓名: {char.get('name', '未知')} | 种族: {char.get('race', '未知')} | 职业: {char.get('character_class', '未知')} | 等级: {char.get('level', 1)}
背景故事: {char.get('backstory', '无')}
性格特征: {chr(10).join(f'  - {k}: {v}' for k, v in personality.items()) if personality else '  未设定'}
个人特质: {', '.join(personal_traits) if personal_traits else '未设定'}
理想/信念: {', '.join(ideals) if ideals else '未设定'}
性格缺陷: {', '.join(flaws) if flaws else '未设定'}
阵营/派系: {faction or '未设定'}
装备: {eq_text or '无'}
技能: {', '.join(char.get('skills', [])) if char.get('skills') else '无'}
""" + (f"""
人际关系:
{rel_text}
""" if rel_text else "") + (f"""
当前目标:
{goals_text}
""" if goals_text else "") + f"""

重要：上面这个角色就是你的玩家。用"你"来称呼他/她。所有关于角色背景、能力的信息以这里的为准。预设剧本中的角色名只是示例，不要强加给玩家。

【角色驱动叙事 — 极其重要】
- 角色背景、性格、关系、装备必须影响你的描述和 NPC 反应
- 不要把玩家当成模板角色，每个角色都是独一无二的
- 如果角色的性格缺陷与当前情境冲突，NPC 会有差异化反应
- 角色的个人特质会影响 NPC 的态度和对话方式
- 角色的阵营/派系决定了 NPC 对玩家的初始态度（盟友/中立/敌对）
- 角色的目标应该引导剧情走向，让玩家有明确的追求
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
当前玩家角色: {self.game_state.character_name} — 你就是这个角色，你的名字是 {self.game_state.character_name}。严格依据上面给出的角色信息来回应，不要把预设剧本中的角色名字强加给玩家。
当前场景: {self.game_state.current_scene or "未设定"}
会话次数: 第 {self.game_state.session_number} 章

作为 TRPG 的 KP，引导玩家冒险。保持剧情连贯，适当设置悬念和挑战。

【叙事格式】
- 自然流畅地叙述，像写小说一样
- 用 **关键词** 标记重要的环境细节、NPC名字、关键物品、动作结果
- 例如：「你推开酒馆的 **橡木门**，**独眼老板**从吧台后面抬起**满是伤疤**的脸」
- 每段2-4句，整体控制在300字以内
- 不要用任何 [TAG] 标记

回复末尾给 3 个行动建议:
[SUGGESTIONS: 建议1 | 建议2 | 建议3]
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

    def build_context_snapshot(self, parent_message_index: int, frontend_messages: list = None) -> Dict[str, Any]:
        """构建分支创建时的完整上下文快照（存入 chat_branches.context_snapshot）

        包含: 场景、角色完整JSON、NPC、任务、地点、对话摘要、世界设定
        前端消息优先（弥补预设开场白不在后端 session 的问题）。
        分支 AI 回复时以此为唯一事实依据，杜绝幻觉。
        """
        gs = self.game_state
        char = gs.selected_character or {}

        # ── 角色完整快照 (JSON) ──
        character_snapshot = {
            "name": char.get("name", gs.character_name),
            "race": char.get("race", ""),
            "class": char.get("character_class", ""),
            "level": char.get("level", 1),
            "hp": gs.character_stats.get("hp", char.get("hp", 10)),
            "ac": gs.character_stats.get("ac", char.get("ac", 10)),
            "attributes": {
                "STR": gs.character_stats.get("STR", 10),
                "DEX": gs.character_stats.get("DEX", 10),
                "CON": gs.character_stats.get("CON", 10),
                "INT": gs.character_stats.get("INT", 10),
                "WIS": gs.character_stats.get("WIS", 10),
                "CHA": gs.character_stats.get("CHA", 10),
            },
            "equipment": char.get("equipment", []) or [],
            "skills": char.get("skills", []) or [],
            "backstory": (char.get("backstory", "") or "")[:300],
            "personality": char.get("personality", {}) or {},
            "faction": char.get("faction", ""),
            "goals": char.get("goals", []) or [],
            "relationships": char.get("relationships", []) or [],
            "personal_traits": char.get("personal_traits", []) or [],
            "ideals": char.get("ideals", []) or [],
            "flaws": char.get("flaws", []) or [],
        }

        # ── 世界状态快照 ──
        world_snapshot = {
            "current_scene": gs.current_scene or self.system_prompt[:200] if self.system_prompt else "",
            "npcs": gs.npcs or [],
            "quests": gs.quests or [],
            "locations": gs.locations or [],
            "world_state": gs.world_state or {},
            "relationship_map": gs.relationship_map or {},
            "combat_active": bool(gs.combat_state and gs.combat_state.get("is_active")),
        }
        if gs.combat_state and gs.combat_state.get("is_active"):
            world_snapshot["combat"] = {
                "round": gs.combat_state.get("round", 1),
                "enemies": gs.enemies or [],
            }

        # ── 世界设定摘要（从 system_prompt 提取） ──
        world_setting = ""
        if self.system_prompt:
            world_setting = self.system_prompt[:500]

        # ── 最近对话摘要 ──
        recent_exchanges = []
        # 优先使用前端传来的对话（弥补预设开场白不在后端 session 的问题）
        source_messages = frontend_messages if frontend_messages else [
            {"role": "玩家" if m.role == "player" else "KP", "content": m.content[:300]}
            for m in self.messages[-16:]
        ]
        if frontend_messages:
            for fm in frontend_messages[-12:]:
                role_label = "玩家" if fm.get("role") == "player" else "KP"
                recent_exchanges.append({
                    "role": role_label,
                    "content": fm.get("content", "")[:300],
                })
        else:
            start = max(0, len(self.messages) - 12)
            for msg in self.messages[start:]:
                role_label = "玩家" if msg.role == "player" else "KP"
                recent_exchanges.append({
                    "role": role_label,
                    "content": msg.content[:300],
                })

        return {
            "snapshot_version": 2,
            "campaign_id": self.campaign_id,
            "world_setting": world_setting,
            "fork_point": {
                "message_index": parent_message_index,
                "session_number": gs.session_number,
            },
            "character": character_snapshot,
            "world": world_snapshot,
            "recent_exchanges": recent_exchanges,
        }

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
            "quests": self.game_state.quests,
            "world_state": self.game_state.world_state,
            "relationship_map": self.game_state.relationship_map,
            "combat_state": self.game_state.combat_state,
            "enemies": self.game_state.enemies,
            "turn_order": self.game_state.turn_order,
            "initiative": self.game_state.initiative,
            "branch_id": self.current_branch_id,
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
        self.game_state.quests = snapshot.get("quests", [])
        self.game_state.world_state = snapshot.get("world_state", {})
        self.game_state.relationship_map = snapshot.get("relationship_map", {})
        self.game_state.combat_state = snapshot.get("combat_state", {})
        self.game_state.enemies = snapshot.get("enemies", [])
        self.game_state.turn_order = snapshot.get("turn_order", [])
        self.game_state.initiative = snapshot.get("initiative", {})

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
    """管理所有活跃的聊天会话（支持 Redis 持久化）"""

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

    @classmethod
    async def save_to_redis(cls, campaign_id: int):
        """将会话持久化到 Redis"""
        session = cls._sessions.get(campaign_id)
        if not session:
            return
        try:
            from services.session_store import SessionStore
            snapshot = session.get_game_snapshot()
            # 额外保存消息摘要
            snapshot["_last_messages"] = [
                {"role": m.role, "content": m.content[:200]}
                for m in session.messages[-10:]
            ]
            await SessionStore.save_session(campaign_id, snapshot)
        except Exception:
            pass  # Redis 不可用时静默降级

    @classmethod
    async def restore_from_redis(cls, campaign_id: int) -> Optional[ChatSession]:
        """尝试从 Redis 恢复会话"""
        try:
            from services.session_store import SessionStore
            data = await SessionStore.load_session(campaign_id)
            if data:
                session = cls.get_or_create_session(campaign_id)
                session.load_from_snapshot(data)
                return session
        except Exception:
            pass
        return None
