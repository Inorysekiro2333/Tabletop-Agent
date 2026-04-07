# Tabletop Agent - 开发待办清单

---

## P0 - 核心体验（必须解决）

- [ ] **记忆持久化**
  - 问题：每次进入战役聊天，之前的记录会清空
  - 方案：使用 Redis 存储会话状态，或迁移到 PostgreSQL
  - 关联issue: #1

---

## P1 - 用户体验优化

- [ ] **思考窗口折叠/展开**
  - KP思考过程显示在可折叠区域
  - 用户可选择展开查看或收起
  - 关联issue: #2

- [ ] **角色卡预设模板**
  - 添加多个预设人设（如：战士、法师、盗贼、猎人等）
  - 随机生成角色（种族+年龄+职业+背景）
  - 关联issue: #3

- [ ] **人设扩展**
  - 添加性格特征（MBTI/大五人格简化版）
  - 添加SAN值（理智值）状态
  - 关联issue: #4

- [ ] **骰子公示增强**
  - 投骰结果大字体动画展示
  - 成功/失败特殊效果
  - 投骰记录历史
  - 关联issue: #7

---

## P2 - 世界构建系统 ⭐ 新增

### 2.1 场景/地图系统

**功能描述：**
- KP可上传图片作为战役地图（.jpg/.png）
- 地图上可标记多个区域（房间、地点）
- 玩家可查看地图并选择移动到不同区域
- 区域触发事件和剧情

**数据模型：**
```
Map {
  id, campaign_id, name, image_url, width, height
}

MapRegion {
  id, map_id, name,
  x, y, width, height,  // 区域坐标
  description,          // 区域描述（进入时显示）
  is_locked, is_hidden
}

PlayerPosition {
  id, session_id, character_id,
  map_id, region_id, x, y
}
```

**UI设计：**
- 左侧：地图展示（可缩放、拖拽）
- 右侧：区域信息面板
- 底部：位置切换按钮

**触发机制：**
- 进入某区域 → 自动推送区域描述
- 特定区域 → 触发剧情事件
- 踩陷阱/搜索 → 自动投骰判定

---

### 2.2 物品/背包系统

**功能描述：**
- 每个角色拥有独立背包
- 物品分类（武器、防具、消耗品、任务道具）
- 物品使用/丢弃/交易
- 关键道具自动记录到剧情

**数据模型：**
```
Item {
  id, name, type, rarity,
  description, effect,
  icon_url, is_consumable
}

CharacterInventory {
  id, character_id, item_id,
  quantity, is_equipped,
  acquired_at, acquired_way
}
```

**物品效果类型：**
- 属性加成（力量+2）
- 投骰加成（对判定+5）
- 一次性使用（药水）
- 剧情钥匙（触发特定事件）

**UI设计：**
- 角色面板新增「背包」Tab
- 物品卡片展示（图标、名称、数量）
- 拖拽装备快捷使用
- 大图标展示稀有物品

---

### 2.3 玩家位置同步

**功能描述：**
- WebSocket实时同步所有玩家位置
- 在地图上显示所有玩家图标
- 位置变化时通知所有玩家
- KP可传送/踢出玩家

---

## P3 - 多人游戏

- [ ] **AI队友模式**
  - 支持用户+AI队友双人跑团
  - AI队友根据角色卡性格自主行动
  - 关联issue: #5

---

## P4 - 智能增强

- [ ] **用户画像分析**
  - 抽取用户行为逻辑
  - 分析玩家性格特征（激进/保守/探索型等）
  - KP根据用户性格调整剧情难度和风格
  - 关联issue: #6

---

## P5 - 内容创作工具

- [ ] **AI剧本生成器**
  - 输入关键词/类型，自动生成剧本框架
  - 生成NPC性格、场景描述、剧情分支
  - 导出为可编辑剧本

---

## 技术债务

- [ ] 添加单元测试
- [ ] API限流保护
- [ ] WebSocket重连优化
- [ ] 数据库索引优化

---

## 推荐Skill（可加速开发）

| 任务 | 推荐Skill | 安装量 | 安装命令 |
|------|-----------|--------|----------|
| Redis集成 | `redis/agent-skills@redis-development` | 1.2K | `npx skills add redis/agent-skills@redis-development -g -y` |
| 后端测试 | `supercent-io/skills-template@backend-testing` | 11.8K | `npx skills add supercent-io/skills-template@backend-testing -g -y` |
| WebApp测试 | `anthropics/skills@webapp-testing` | 35.8K | `npx skills add anthropics/skills@webapp-testing -g -y` |

---

## 优先级建议

| 优先级 | 功能 | 理由 |
|--------|------|------|
| P0 | 记忆持久化 | 核心体验，数据丢失问题 |
| P1 | 思考窗口折叠 | 用户反馈强烈 |
| P1 | 骰子公示增强 | 视觉反馈优化 |
| P2 | 场景/地图系统 | 世界构建核心，带来沉浸感 |
| P2 | 物品/背包系统 | RPG核心系统 |
| P2 | AI队友 | 差异化竞争点 |
| P3 | 用户画像 | 长期智能化的基础 |
