/**
 * 职业预设 — 所有职业的初始属性、技能、装备均由此 JSON 控制
 *
 * 规则:
 *   - 6 项属性 (STR/DEX/CON/INT/WIS/CHA) 基础值总和 = 25
 *   - 玩家创建时可分配 5 点额外属性 (剩余点在 UI 显示)
 *   - 最终属性 = 基础值 + 分配值
 *   - 每个职业 1 个初始技能 + 1-2 个初始装备
 */

export interface ClassPreset {
  key: string;
  label: string;
  baseAttributes: { STR: number; DEX: number; CON: number; INT: number; WIS: number; CHA: number };
  defaultSkills: string[];
  defaultEquipment: string[];
  description: string;
}

export const BONUS_ATTRIBUTE_POINTS = 6;
export const TOTAL_ATTRIBUTE_SUM = 36; // 30 base + 6 bonus

export const CLASS_PRESETS: ClassPreset[] = [
  {
    key: '战士',
    label: '战士',
    baseAttributes: { STR: 8, DEX: 5, CON: 7, INT: 3, WIS: 4, CHA: 3 },
    defaultSkills: ['近战攻击'],
    defaultEquipment: ['长剑', '皮甲'],
    description: '前线战斗专家，擅长近战武器和承受伤害',
  },
  {
    key: '法师',
    label: '法师',
    baseAttributes: { STR: 2, DEX: 4, CON: 4, INT: 9, WIS: 7, CHA: 4 },
    defaultSkills: ['奥术知识'],
    defaultEquipment: ['法杖', '法术书'],
    description: '奥术能量的操控者，掌握强大的攻击性和防御性法术',
  },
  {
    key: '盗贼',
    label: '盗贼',
    baseAttributes: { STR: 4, DEX: 9, CON: 4, INT: 5, WIS: 4, CHA: 4 },
    defaultSkills: ['潜行'],
    defaultEquipment: ['匕首', '盗贼工具'],
    description: '潜行与诡计大师，擅长开锁、暗杀和隐匿行动',
  },
  {
    key: '牧师',
    label: '牧师',
    baseAttributes: { STR: 4, DEX: 4, CON: 5, INT: 5, WIS: 9, CHA: 3 },
    defaultSkills: ['医疗'],
    defaultEquipment: ['圣徽', '链甲'],
    description: '神圣魔法的施法者，擅长治疗、驱魔和防护法术',
  },
  {
    key: '游侠',
    label: '游侠',
    baseAttributes: { STR: 5, DEX: 7, CON: 5, INT: 4, WIS: 6, CHA: 3 },
    defaultSkills: ['追踪'],
    defaultEquipment: ['长弓', '箭袋'],
    description: '荒野中的猎手，精通远程攻击、野外生存和追踪',
  },
  {
    key: '吟游诗人',
    label: '吟游诗人',
    baseAttributes: { STR: 3, DEX: 5, CON: 4, INT: 5, WIS: 4, CHA: 9 },
    defaultSkills: ['表演'],
    defaultEquipment: ['鲁特琴', '华丽服饰'],
    description: '以音乐和故事施法的艺术家，擅长社交、鼓舞和魅惑',
  },
  {
    key: '德鲁伊',
    label: '德鲁伊',
    baseAttributes: { STR: 4, DEX: 4, CON: 5, INT: 5, WIS: 9, CHA: 3 },
    defaultSkills: ['自然知识'],
    defaultEquipment: ['橡木杖', '草药包'],
    description: '自然之力的化身，擅长变形、召唤动物和元素魔法',
  },
  {
    key: '圣骑士',
    label: '圣骑士',
    baseAttributes: { STR: 7, DEX: 4, CON: 6, INT: 4, WIS: 5, CHA: 4 },
    defaultSkills: ['宗教知识'],
    defaultEquipment: ['长剑', '盾牌'],
    description: '神圣誓言约束的战士，兼具近战能力和治疗神术',
  },
  {
    key: '术士',
    label: '术士',
    baseAttributes: { STR: 3, DEX: 4, CON: 5, INT: 6, WIS: 5, CHA: 7 },
    defaultSkills: ['欺瞒'],
    defaultEquipment: ['魔杖', '符文石'],
    description: '天生具有魔法血脉，以魅力施法，掌握超魔技巧',
  },
  {
    key: '学生',
    label: '学生',
    baseAttributes: { STR: 3, DEX: 4, CON: 4, INT: 8, WIS: 6, CHA: 5 },
    defaultSkills: ['知识检定'],
    defaultEquipment: ['笔记本', '钢笔'],
    description: '求知若渴的年轻学者，擅长分析与推理，潜力无限',
  },
];

/** 根据职业 key 查找预设 */
export function getClassPreset(classKey: string): ClassPreset | undefined {
  return CLASS_PRESETS.find(c => c.key === classKey);
}
