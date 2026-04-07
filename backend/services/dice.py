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
