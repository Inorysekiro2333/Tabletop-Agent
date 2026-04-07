"""
Character Generator Service - AI 生成 D&D 角色卡
"""
import json
from typing import Dict, Any
from services.ai_gateway import AIGateway


CHARACTER_GENERATION_PROMPT = """你是一位专业的D&D 5e角色设计专家。请根据以下要求生成一个角色卡：

{preferences}

请以严格的JSON格式返回，包含以下字段：
- name: 角色名（奇幻风格）
- race: 种族（如人类精灵矮人等）
- class: 职业（如战士、法师、盗贼等）
- level: 等级（默认为1）
- attributes: 属性对象，包含STR、DEX、CON、INT、WIS、CHA，值为3-18之间的整数
- hp: 生命值（根据职业和体质计算）
- ac: 护甲等级（根据职业和敏捷计算）
- skills: 技能列表（字符串数组）
- backstory: 背景故事（2-3句话）
- personality: 性格对象，包含trait、ideal、bond、flaw四个字段

只返回JSON，不要包含任何其他文字。"""

DEFAULT_ATTRIBUTES = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10, "CHA": 10}


def parse_attributes(attributes_dict: Dict[str, Any]) -> Dict[str, int]:
    """解析属性，确保值在有效范围内"""
    result = DEFAULT_ATTRIBUTES.copy()
    for key, value in attributes_dict.items():
        if key.upper() in result and isinstance(value, int):
            result[key.upper()] = max(3, min(18, value))
    return result


async def generate_character(
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    race_preference: str = None,
    class_preference: str = None,
    personality_hints: str = None
) -> Dict[str, Any]:
    """使用 AI 生成角色卡"""

    # 构建偏好描述
    preferences = []
    if race_preference:
        preferences.append(f"种族偏好：{race_preference}")
    if class_preference:
        preferences.append(f"职业偏好：{class_preference}")
    if personality_hints:
        preferences.append(f"性格要求：{personality_hints}")

    if not preferences:
        preferences.append("请自由设计一个有趣的冒险者角色")

    prompt = CHARACTER_GENERATION_PROMPT.format(preferences="\n".join(preferences))

    messages = [
        {"role": "user", "content": prompt}
    ]

    try:
        response = await AIGateway.chat(
            provider_name=provider,
            messages=messages,
            model=model,
            api_key=api_key,
            base_url=base_url
        )

        # 尝试解析 JSON
        # 去除 markdown 代码块标记
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        character_data = json.loads(response)

        # 验证并规范化属性
        if "attributes" in character_data:
            character_data["attributes"] = parse_attributes(character_data["attributes"])

        return character_data

    except json.JSONDecodeError as e:
        raise ValueError(f"AI 返回的 JSON 格式无效: {e}\n原始响应: {response[:500]}")
    except Exception as e:
        raise RuntimeError(f"生成角色卡失败: {e}")
