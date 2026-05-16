"""
Dice Service - D&D 投骰系统
支持各种骰子格式和规则判定
"""
import random
import re
from typing import Tuple, List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DiceRoll:
    """投骰结果"""
    dice_type: str  # e.g., "1d20", "2d6"
    rolls: List[int]  # 每次掷骰的结果
    modifier: int  # 修正值
    total: int  # 最终总计
    success: Optional[bool] = None  # 是否成功（用于有DC的判定）
    description: str = ""  # 描述


def roll_dice(dice_str: str, modifier: int = 0) -> DiceRoll:
    """
    解析骰子字符串并投骰

    支持格式:
    - "d20" 或 "1d20" - 单个d20
    - "2d6" - 两个d6
    - "1d20+5" - d20 + 5修正
    - "1d20-2" - d20 - 2修正
    - "4d6kh3" - 4d6，保留最高3个（用于属性生成）
    """
    dice_str = dice_str.lower().strip()

    # 解析修正值
    modifier_match = re.search(r'([+-]\d+)$', dice_str)
    if modifier_match:
        modifier = int(modifier_match.group(1))
        dice_str = dice_str[:modifier_match.start()]

    # 解析骰子数量和面数
    # 格式: NdX 或 NdXkhN 或 NdXklN
    match = re.match(r'(\d*)d(\d+)(kh\d+|kl\d+)?', dice_str)
    if not match:
        raise ValueError(f"无效的骰子格式: {dice_str}")

    count_str, faces_str, keep_str = match.groups()

    # 骰子数量默认为1
    count = int(count_str) if count_str else 1
    faces = int(faces_str)

    # 投骰
    rolls = [random.randint(1, faces) for _ in range(count)]

    # 处理保留规则 (keep highest / keep lowest)
    if keep_str:
        if keep_str.startswith('kh'):
            keep_count = int(keep_str[2:])
            rolls = sorted(rolls, reverse=True)[:keep_count]
        elif keep_str.startswith('kl'):
            keep_count = int(keep_str[2:])
            rolls = sorted(rolls)[:keep_count]

    total = sum(rolls) + modifier

    return DiceRoll(
        dice_type=f"{count}d{faces}",
        rolls=rolls,
        modifier=modifier,
        total=total,
        description=f"{count}d{faces} [{', '.join(map(str, rolls))}]" +
                   (f" {'+' if modifier >= 0 else ''}{modifier}" if modifier != 0 else "")
    )


def roll_initiative(dex_modifier: int = 0) -> DiceRoll:
    """投先攻"""
    return roll_dice("d20", dex_modifier)


def roll_attack(attack_bonus: int, target_ac: int) -> DiceRoll:
    """投攻击判定"""
    result = roll_dice("d20", attack_bonus)
    result.success = result.total >= target_ac
    result.description += f" vs AC {target_ac}"
    return result


def roll_saving_throw(dc: int, proficiency_bonus: int = 0, ability_modifier: int = 0) -> DiceRoll:
    """投豁免判定"""
    modifier = proficiency_bonus + ability_modifier
    result = roll_dice("d20", modifier)
    result.success = result.total >= dc
    result.description += f" vs DC {dc}"
    return result


def roll_skill_check(dc: int, proficiency_bonus: int = 0, ability_modifier: int = 0) -> DiceRoll:
    """投技能检定"""
    return roll_saving_throw(dc, proficiency_bonus, ability_modifier)


def roll_damage(damage_dice: str, modifier: int = 0) -> DiceRoll:
    """投伤害"""
    return roll_dice(damage_dice, modifier)


def roll_ability_check(ability_modifier: int = 0) -> DiceRoll:
    """投属性检定 (纯粹1d20+修正)"""
    return roll_dice("d20", ability_modifier)


def roll_with_advantage(disadvantage: bool = False) -> Tuple[DiceRoll, DiceRoll]:
    """投具有优势/劣势的判定"""
    roll1 = roll_dice("d20")
    roll2 = roll_dice("d20")

    if disadvantage:
        # 取较低值
        if roll2.total < roll1.total:
            roll1, roll2 = roll2, roll1
        roll1.description = f"{roll1.dice_type} [{roll1.rolls[0]}] (disadvantage)"
    else:
        # 取较高值
        if roll2.total > roll1.total:
            roll1, roll2 = roll2, roll1
        roll1.description = f"{roll1.dice_type} [{roll1.rolls[0]}] (advantage)"

    return roll1, roll2


def format_dice_result(result: DiceRoll, context: str = "") -> str:
    """格式化投骰结果为字符串"""
    success_str = ""
    if result.success is True:
        success_str = " ✅ 成功!"
    elif result.success is False:
        success_str = " ❌ 失败!"

    context_str = f" ({context})" if context else ""

    return f"🎲 {result.description} = **{result.total}**{success_str}{context_str}"


def parse_dice_command(command: str) -> Optional[DiceRoll]:
    """
    解析玩家输入的投骰命令

    支持格式:
    - "1d20" - 1d20
    - "d20+5" - d20+5
    - "2d6" - 2d6
    - "1d20" 或 "d20" - d20
    - "r 1d20" - r = roll
    - "投 1d20" - 中文
    """
    command = command.lower().strip()

    # 移除常见前缀
    prefixes_to_remove = ['roll', 'r', '投', '掷', '扔', '丢']
    for prefix in prefixes_to_remove:
        if command.startswith(prefix):
            command = command[len(prefix):].strip()

    # 如果包含空格，尝试取第一部分
    if ' ' in command:
        command = command.split()[0]

    # 尝试解析
    try:
        # 添加缺失的1
        if command.startswith('d'):
            command = '1' + command

        return roll_dice(command)
    except ValueError:
        return None


# D&D 5e 常用骰子模板
DICE_TEMPLATES = {
    "d20": "d20",
    "d100": "d100",
    "d20+5": "1d20+5",
    "2d6": "2d6",
    "8d6": "8d6",  # 火球
    "4d6kh3": "4d6kh3",  # 属性生成
}


# ═══════════════════════════════════════════
# 规则判定引擎 (Goal 3)
# ═══════════════════════════════════════════

def calculate_ac(character: dict) -> int:
    """计算角色护甲等级"""
    base_ac = character.get("ac", 10)
    equipment = character.get("equipment", []) or []
    attributes = character.get("attributes", {}) or {}
    dex_mod = (attributes.get("DEX", 10) - 10) // 2

    # 检查装备中的护甲
    armor_ac = 0
    shield_bonus = 0
    for item in equipment:
        item_name = item.get("name", str(item)).lower() if isinstance(item, dict) else str(item).lower()
        if "皮甲" in item_name or "leather" in item_name:
            armor_ac = max(armor_ac, 11 + dex_mod)
        elif "链甲" in item_name or "chain" in item_name:
            armor_ac = max(armor_ac, 13 + max(0, min(2, dex_mod)))
        elif "板甲" in item_name or "plate" in item_name:
            armor_ac = max(armor_ac, 18)
            dex_mod = 0  # 板甲无敏捷加成
        elif "盾" in item_name or "shield" in item_name:
            shield_bonus = 2

    return max(base_ac, armor_ac) + shield_bonus


def get_ability_modifier(character: dict, ability: str) -> int:
    """获取属性调整值"""
    attributes = character.get("attributes", {}) or {}
    score = attributes.get(ability.upper(), 10)
    return (score - 10) // 2


def resolve_attack(attacker: dict, defender: dict, attack_bonus: int = 0,
                   damage_dice: str = "1d6", damage_bonus: int = 0) -> dict:
    """解析攻击判定，返回统一结果结构"""
    target_ac = calculate_ac(defender)

    # 攻击掷骰
    atk_roll = roll_dice("d20", attack_bonus)
    hit = atk_roll.total >= target_ac
    is_crit = atk_roll.rolls[0] == 20
    is_fumble = atk_roll.rolls[0] == 1

    # 伤害掷骰
    dmg_roll = roll_dice(damage_dice, damage_bonus) if hit else DiceRoll(dice_type=damage_dice, rolls=[0], modifier=0, total=0)
    if is_crit and hit:
        # 暴击：伤害骰翻倍
        dmg_roll = roll_dice(damage_dice.replace("1d", "2d") if damage_dice.startswith("1d") else damage_dice, damage_bonus)

    result = {
        "success": hit,
        "attack_roll": atk_roll.rolls[0],
        "attack_total": atk_roll.total,
        "target_ac": target_ac,
        "damage": dmg_roll.total,
        "damage_roll": dmg_roll.rolls,
        "damage_dice": damage_dice,
        "is_crit": is_crit,
        "is_fumble": is_fumble,
    }

    # 构建描述
    atk_desc = f"攻击判定 d20+{attack_bonus}={atk_roll.total} vs AC{target_ac}"
    if is_fumble:
        result["description"] = f"{atk_desc} — 大失败！攻击失误"
    elif is_crit:
        result["description"] = f"{atk_desc} — 暴击！造成 {dmg_roll.total} 点伤害"
    elif hit:
        result["description"] = f"{atk_desc} — 命中！造成 {dmg_roll.total} 点伤害"
    else:
        result["description"] = f"{atk_desc} — 未命中"

    return result


def resolve_skill_check(character: dict, skill: str, dc: int) -> dict:
    """解析技能检定"""
    attributes = character.get("attributes", {}) or {}
    skills = character.get("skills", []) or []

    # 技能对应的属性映射
    skill_abilities = {
        "stealth": "DEX", "athletics": "STR", "acrobatics": "DEX",
        "sleight_of_hand": "DEX", "investigation": "INT", "perception": "WIS",
        "survival": "WIS", "insight": "WIS", "persuasion": "CHA",
        "intimidation": "CHA", "deception": "CHA", "performance": "CHA",
        "arcana": "INT", "history": "INT", "nature": "INT", "religion": "INT",
        "medicine": "WIS", "animal_handling": "WIS",
    }
    ability = skill_abilities.get(skill.lower(), "DEX")
    ability_mod = get_ability_modifier(character, ability)

    # 熟练加值（简化：等级/4 + 1）
    level = character.get("level", 1)
    prof_bonus = (level - 1) // 4 + 2
    is_proficient = any(s.lower() == skill.lower() for s in skills)
    total_mod = ability_mod + (prof_bonus if is_proficient else 0)

    roll = roll_dice("d20", total_mod)
    success = roll.total >= dc

    return {
        "success": success,
        "roll": roll.rolls[0],
        "total": roll.total,
        "dc": dc,
        "skill": skill,
        "ability": ability,
        "proficient": is_proficient,
        "description": f"{skill}检定 d20+{total_mod}={roll.total} vs DC{dc} — {'成功' if success else '失败'}",
    }


def resolve_saving_throw(character: dict, dc: int, ability: str) -> dict:
    """解析豁免检定"""
    ability_mod = get_ability_modifier(character, ability)
    roll = roll_dice("d20", ability_mod)
    success = roll.total >= dc

    return {
        "success": success,
        "roll": roll.rolls[0],
        "total": roll.total,
        "dc": dc,
        "ability": ability.upper(),
        "description": f"{ability.upper()}豁免 d20+{ability_mod}={roll.total} vs DC{dc} — {'成功' if success else '失败'}",
    }


def apply_condition(character: dict, condition: str, duration: int) -> dict:
    """应用状态效果"""
    conditions = character.get("conditions", []) or []
    conditions.append({"name": condition, "duration": duration})
    result = dict(character)
    result["conditions"] = conditions
    result["description"] = f"获得状态: {condition}（持续{duration}回合）"
    return result


# 伤害骰映射（常见武器/法术）
DAMAGE_DICE_MAP = {
    "短剑": "1d6", "长剑": "1d8", "巨剑": "2d6",
    "匕首": "1d4", "手斧": "1d6", "战斧": "1d8",
    "短弓": "1d6", "长弓": "1d8", "弩": "1d10",
    "火球": "8d6", "魔法飞弹": "3d4+3", "火焰箭": "1d10",
    "短sword": "1d6", "长剑sword": "1d8", "巨sword": "2d6",
    "dagger": "1d4", "axe": "1d6", "战axe": "1d8",
    "shortbow": "1d6", "longbow": "1d8", "crossbow": "1d10",
    "fireball": "8d6", "magic_missile": "3d4+3", "fire_bolt": "1d10",
}


def detect_combat_intent(message: str) -> Optional[dict]:
    """检测消息中的战斗/动作意图"""
    import re
    msg_lower = message.lower()

    # 攻击意图
    attack_patterns = [
        r'(?:我|我用|使用)?攻击\s*(.+)',
        r'(?:我|我用|使用)?砍\s*(.+)',
        r'(?:我|我用|使用)?射\s*(.+)',
        r'(?:我|我用|使用)?打\s*(.+)',
        r'(?:i\s+)?attack\s+(.+)',
    ]
    for pattern in attack_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            target = match.group(1).strip()
            # 检测武器类型
            weapon = None
            for w in DAMAGE_DICE_MAP:
                if w.lower() in msg_lower:
                    weapon = w
                    break
            return {
                "action_type": "attack",
                "target": target,
                "weapon": weapon or "短剑",
                "damage_dice": DAMAGE_DICE_MAP.get(weapon, "1d6") if weapon else "1d6",
            }

    # 技能检定
    skill_pattern = r'(?:/skill|技能|检定)\s*(\w+)\s*(?:dc\s*(\d+))?'
    match = re.search(skill_pattern, msg_lower)
    if match:
        skill = match.group(1)
        dc = int(match.group(2)) if match.group(2) else 15
        return {"action_type": "skill_check", "skill": skill, "dc": dc}

    # 施法
    cast_pattern = r'(?:/cast|施法|释放|cast)\s*(.+)'
    match = re.search(cast_pattern, msg_lower)
    if match:
        spell = match.group(1).strip()
        return {"action_type": "cast", "spell": spell, "damage_dice": DAMAGE_DICE_MAP.get(spell, "1d6")}

    # 使用物品
    use_pattern = r'(?:/use|使用|喝下|服用)\s*(.+)'
    match = re.search(use_pattern, msg_lower)
    if match:
        item = match.group(1).strip()
        return {"action_type": "use_item", "item": item}

    return None


def parse_action_command(message: str) -> Optional[dict]:
    """解析玩家输入的动作命令（/attack, /skill, /cast, /use 前缀）"""
    msg = message.strip()

    # /attack <target> [with <weapon>]
    if msg.startswith("/attack") or msg.startswith("/攻击"):
        parts = msg.split(maxsplit=2)
        target = parts[1] if len(parts) > 1 else "敌人"
        weapon = None
        if len(parts) > 2:
            weapon_part = parts[2]
            for w in DAMAGE_DICE_MAP:
                if w in weapon_part:
                    weapon = w
                    break
        return {
            "action_type": "attack",
            "target": target,
            "weapon": weapon or "短剑",
            "damage_dice": DAMAGE_DICE_MAP.get(weapon, "1d6") if weapon else "1d6",
        }

    # /skill <name> dc<NN>
    if msg.startswith("/skill") or msg.startswith("/技能"):
        import re
        skill_match = re.search(r'(?:/skill|/技能)\s+(\w+)(?:\s+dc\s*(\d+))?', msg, re.IGNORECASE)
        if skill_match:
            return {
                "action_type": "skill_check",
                "skill": skill_match.group(1),
                "dc": int(skill_match.group(2)) if skill_match.group(2) else 15,
            }

    # /cast <spell>
    if msg.startswith("/cast") or msg.startswith("/施法"):
        parts = msg.split(maxsplit=1)
        spell = parts[1].strip() if len(parts) > 1 else "magic_missile"
        return {
            "action_type": "cast",
            "spell": spell,
            "damage_dice": DAMAGE_DICE_MAP.get(spell, "1d6"),
        }

    # /use <item>
    if msg.startswith("/use") or msg.startswith("/使用"):
        parts = msg.split(maxsplit=1)
        item = parts[1].strip() if len(parts) > 1 else "potion"
        return {"action_type": "use_item", "item": item}

    # Fallback: 自然语言检测
    return detect_combat_intent(msg)
