import { useEffect, useState, useCallback } from 'react';
import { Modal, Form, Input, InputNumber, Select, Button, Divider, Tag } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { characterAPI } from '../services/api';
import type { Character } from '../services/api';
import { CLASS_PRESETS, BONUS_ATTRIBUTE_POINTS, getClassPreset, type ClassPreset } from '../data/classPresets';

interface Props {
  visible: boolean;
  character: Character | null;
  onClose: () => void;
  onSuccess: () => void;
}

const RACES = ['人类', '精灵', '矮人', '半身人', '兽人', '龙裔', '半精灵', '提夫林'];
const GOAL_STATUSES = ['进行中', '已完成', '搁置'];
const RELATION_TYPES = ['盟友', '敌人', '中立', '家人', '导师', '恋人', '朋友'];
const RELATION_ATTITUDES = ['友好', '冷淡', '敌对', '尊敬', '怀疑'];

const ATTR_KEYS = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA'] as const;
const ATTR_LABELS: Record<string, string> = { STR: '力量', DEX: '敏捷', CON: '体质', INT: '智力', WIS: '感知', CHA: '魅力' };

function toGoalArray(arr: any): Array<{ name: string; description: string; status: string }> {
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map((item: any) => ({
    name: typeof item === 'string' ? item : item.name || '',
    description: typeof item === 'object' ? item.description || '' : '',
    status: typeof item === 'object' ? item.status || '进行中' : '进行中',
  }));
}

function toRelationArray(arr: any): Array<{ name: string; type: string; description: string; attitude: string }> {
  if (!arr || !Array.isArray(arr)) return [];
  return arr.map((item: any) => ({
    name: typeof item === 'string' ? item : item.name || '',
    type: typeof item === 'object' ? item.type || '' : '',
    description: typeof item === 'object' ? item.description || '' : '',
    attitude: typeof item === 'object' ? item.attitude || '' : '',
  }));
}

export function CharacterModal({ visible, character, onClose, onSuccess }: Props) {
  const [form] = Form.useForm();
  const isEdit = character !== null;

  // Point-buy state
  const [baseAttrs, setBaseAttrs] = useState<Record<string, number>>({});
  const [bonusUsed, setBonusUsed] = useState<Record<string, number>>({});
  const [selectedClass, setSelectedClass] = useState<string>('');
  const [classPreset, setClassPreset] = useState<ClassPreset | null>(null);

  const remainingPoints = BONUS_ATTRIBUTE_POINTS - Object.values(bonusUsed).reduce((a, b) => a + b, 0);

  // Apply class preset — set base attributes, equipment, skills
  const applyPreset = useCallback((classKey: string) => {
    const preset = getClassPreset(classKey);
    if (!preset) return;
    setClassPreset(preset);
    setSelectedClass(classKey);
    setBaseAttrs({ ...preset.baseAttributes });
    setBonusUsed({ STR: 0, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 0 });

    // Update form fields
    for (const attr of ATTR_KEYS) {
      form.setFieldValue(`attributes_${attr}`, preset.baseAttributes[attr]);
    }
    form.setFieldValue('skills', [...preset.defaultSkills]);
    form.setFieldValue('equipment', [...preset.defaultEquipment]);
  }, [form]);

  // Handle attribute change — track bonus points consumed
  const handleAttrChange = (attr: string, value: number | null) => {
    const val = value ?? 0;
    const base = baseAttrs[attr] ?? 0;
    const delta = val - base;
    if (delta < 0) return; // can't go below base

    // Calculate how many points are already used by OTHER attributes
    const othersUsed = Object.entries(bonusUsed)
      .filter(([k]) => k !== attr)
      .reduce((sum, [, v]) => sum + v, 0);

    const maxForThis = BONUS_ATTRIBUTE_POINTS - othersUsed;
    const clamped = Math.min(delta, maxForThis);

    setBonusUsed(prev => ({ ...prev, [attr]: clamped }));
    form.setFieldValue(`attributes_${attr}`, base + clamped);
  };

  // Sync form when opening
  useEffect(() => {
    if (!visible) return;

    if (character) {
      // Edit mode — load character data
      const charClass = character.character_class || '';
      const preset = getClassPreset(charClass);
      const attrs = character.attributes || { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 };

      if (preset) {
        setClassPreset(preset);
        setSelectedClass(charClass);
        setBaseAttrs({ ...preset.baseAttributes });
        // Calculate bonus from saved attributes vs preset base
        const bonus: Record<string, number> = {};
        for (const attr of ATTR_KEYS) {
          bonus[attr] = Math.max(0, (attrs[attr] ?? 10) - (preset.baseAttributes[attr] ?? 0));
        }
        setBonusUsed(bonus);
      } else {
        setBaseAttrs({ STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 });
        setBonusUsed({ STR: 0, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 0 });
        setClassPreset(null);
      }

      form.setFieldsValue({
        name: character.name,
        race: character.race || undefined,
        character_class: charClass || undefined,
        level: character.level,
        hp: character.hp,
        ac: character.ac,
        attributes_STR: attrs.STR ?? 10,
        attributes_DEX: attrs.DEX ?? 10,
        attributes_CON: attrs.CON ?? 10,
        attributes_INT: attrs.INT ?? 10,
        attributes_WIS: attrs.WIS ?? 10,
        attributes_CHA: attrs.CHA ?? 10,
        skills: character.skills || [],
        equipment: character.equipment || [],
        faction: character.faction || '',
        personal_traits: character.personal_traits || [],
        ideals: character.ideals || [],
        flaws: character.flaws || [],
        backstory: character.backstory || '',
        goals: toGoalArray(character.goals),
        relationships: toRelationArray(character.relationships),
      });
    } else {
      // Create mode — reset
      form.resetFields();
      setClassPreset(null);
      setSelectedClass('');
      setBaseAttrs({});
      setBonusUsed({ STR: 0, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 0 });
    }
  }, [visible, character, form]);

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const payload: Record<string, any> = {
      name: values.name,
      race: values.race || null,
      character_class: values.character_class || null,
      level: values.level || 1,
      hp: values.hp || 10,
      ac: values.ac || 10,
      attributes: {
        STR: values.attributes_STR ?? 10,
        DEX: values.attributes_DEX ?? 10,
        CON: values.attributes_CON ?? 10,
        INT: values.attributes_INT ?? 10,
        WIS: values.attributes_WIS ?? 10,
        CHA: values.attributes_CHA ?? 10,
      },
      skills: values.skills || [],
      equipment: values.equipment || [],
      backstory: values.backstory || null,
      faction: values.faction || null,
      personal_traits: values.personal_traits || [],
      ideals: values.ideals || [],
      flaws: values.flaws || [],
      goals: (values.goals || []).map((g: any) => ({
        name: g.name,
        description: g.description || '',
        status: g.status || '进行中',
      })),
      relationships: (values.relationships || []).map((r: any) => ({
        name: r.name,
        type: r.type || '',
        description: r.description || '',
        attitude: r.attitude || '',
      })),
    };

    try {
      if (isEdit) {
        await characterAPI.update(character!.id, payload);
      } else {
        await characterAPI.create(payload);
      }
      onSuccess();
      onClose();
    } catch {
      // error handled by interceptor
    }
  };

  const classOptions = CLASS_PRESETS.map(c => ({
    label: `${c.label} — ${c.description.slice(0, 20)}...`,
    value: c.key,
  }));

  return (
    <Modal
      title={isEdit ? '编辑角色卡' : '创建角色卡'}
      open={visible}
      onCancel={onClose}
      onOk={handleSubmit}
      okText={isEdit ? '保存' : '创建'}
      cancelText="取消"
      width={680}
      styles={{ body: { maxHeight: '70vh', overflowY: 'auto' } }}
    >
      <Form form={form} layout="vertical" initialValues={{ level: 1, hp: 10, ac: 10 }}>
        {/* ── 基础信息 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>基础信息</Divider>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item name="name" label="角色名" rules={[{ required: true, message: '请输入角色名' }]}>
            <Input placeholder="例如：甘道夫" />
          </Form.Item>
          <Form.Item name="level" label="等级">
            <InputNumber min={1} max={20} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="race" label="种族">
            <Select placeholder="选择种族" allowClear options={RACES.map(r => ({ label: r, value: r }))} />
          </Form.Item>
          <Form.Item name="character_class" label="职业">
            <Select
              placeholder="选择职业（自动填充属性和装备）"
              allowClear
              options={classOptions}
              onChange={(val) => {
                if (val) applyPreset(val);
                else {
                  setClassPreset(null);
                  setSelectedClass('');
                  setBaseAttrs({});
                  setBonusUsed({ STR: 0, DEX: 0, CON: 0, INT: 0, WIS: 0, CHA: 0 });
                }
              }}
            />
          </Form.Item>
          <Form.Item name="hp" label="生命值 (HP)">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="ac" label="护甲等级 (AC)">
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
        </div>

        {/* ── 属性值 (Point-buy) ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>
          六维属性
          {classPreset && (
            <span style={{ marginLeft: 8, fontWeight: 'normal' }}>
              可分配点数: <Tag color={remainingPoints > 0 ? 'gold' : 'default'} style={{ marginLeft: 4 }}>{remainingPoints}</Tag>
            </span>
          )}
        </Divider>
        {classPreset && (
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 12 }}>
            <em>{classPreset.description}</em> — 基础值已自动填入，可调整（每点+1，共 {BONUS_ATTRIBUTE_POINTS} 点可分配）
          </div>
        )}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0 12px' }}>
          {ATTR_KEYS.map(attr => (
            <Form.Item key={attr} name={`attributes_${attr}`} label={`${attr} (${ATTR_LABELS[attr]})`}>
              <InputNumber
                min={baseAttrs[attr] ?? 0}
                max={30}
                style={{ width: '100%' }}
                onChange={(val) => handleAttrChange(attr, val)}
                disabled={!classPreset && !isEdit}
              />
            </Form.Item>
          ))}
        </div>

        {/* ── 技能与装备 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>技能 / 装备</Divider>
        <Form.Item name="skills" label="技能">
          <Select mode="tags" placeholder="输入技能名称，回车添加" />
        </Form.Item>
        <Form.Item name="equipment" label="装备 / 物品">
          <Select mode="tags" placeholder="输入装备名称，回车添加" />
        </Form.Item>

        {/* ── 身份与性格 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>身份 / 性格</Divider>
        <Form.Item name="faction" label="阵营">
          <Input placeholder="例如：竖琴手同盟" />
        </Form.Item>
        <Form.Item name="personal_traits" label="个人特质">
          <Select mode="tags" placeholder="例如：勇敢、好奇心旺盛" />
        </Form.Item>
        <Form.Item name="ideals" label="理想 / 信念">
          <Select mode="tags" placeholder="例如：保护弱小、追求真理" />
        </Form.Item>
        <Form.Item name="flaws" label="性格缺陷">
          <Select mode="tags" placeholder="例如：容易轻信他人、恐高" />
        </Form.Item>

        {/* ── 背景故事 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>背景故事</Divider>
        <Form.Item name="backstory" label="背景">
          <Input.TextArea rows={4} placeholder="描述角色的出身、经历和冒险动机..." />
        </Form.Item>

        {/* ── 目标 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '0 0 12px' }}>当前目标</Divider>
        <Form.List name="goals">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...rest }) => (
                <div key={key} style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems: 'flex-start' }}>
                  <Form.Item {...rest} name={[name, 'name']} style={{ flex: 2, margin: 0 }} rules={[{ required: true, message: '目标名称' }]}>
                    <Input placeholder="目标名称" />
                  </Form.Item>
                  <Form.Item {...rest} name={[name, 'status']} style={{ width: 100, margin: 0 }} initialValue="进行中">
                    <Select options={GOAL_STATUSES.map(s => ({ label: s, value: s }))} />
                  </Form.Item>
                  <Button icon={<DeleteOutlined />} size="small" danger onClick={() => remove(name)} />
                </div>
              ))}
              <Button type="dashed" onClick={() => add({ name: '', status: '进行中' })} block icon={<PlusOutlined />}>
                添加目标
              </Button>
            </>
          )}
        </Form.List>

        {/* ── 人际关系 ── */}
        <Divider plain style={{ fontSize: 12, color: 'var(--color-text-muted)', margin: '12px 0' }}>人际关系</Divider>
        <Form.List name="relationships">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...rest }) => (
                <div key={key} style={{ border: '1px solid var(--color-border)', borderRadius: 8, padding: 12, marginBottom: 8, position: 'relative' }}>
                  <Button
                    icon={<DeleteOutlined />} size="small" danger
                    style={{ position: 'absolute', top: 8, right: 8 }}
                    onClick={() => remove(name)}
                  />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 12px' }}>
                    <Form.Item {...rest} name={[name, 'name']} label="姓名" rules={[{ required: true, message: '角色名' }]}>
                      <Input placeholder="NPC 名称" />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'type']} label="关系类型">
                      <Select placeholder="选择类型" allowClear options={RELATION_TYPES.map(t => ({ label: t, value: t }))} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'attitude']} label="态度">
                      <Select placeholder="选择态度" allowClear options={RELATION_ATTITUDES.map(a => ({ label: a, value: a }))} />
                    </Form.Item>
                    <Form.Item {...rest} name={[name, 'description']} label="描述">
                      <Input placeholder="简短描述" />
                    </Form.Item>
                  </div>
                </div>
              ))}
              <Button type="dashed" onClick={() => add({ name: '', type: '', attitude: '', description: '' })} block icon={<PlusOutlined />}>
                添加关系
              </Button>
            </>
          )}
        </Form.List>
      </Form>
    </Modal>
  );
}
