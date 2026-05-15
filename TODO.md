# Tabletop Agent - 开发待办清单

---

## ✅ 已完成

- [x] **前端暗幕主题重设计**
  - 暗黑/亮色主题切换（OKLCH 色彩空间）
  - Grimoire 风格侧边栏导航
  - 登录/注册页品牌化
  - 全局 Ant Design 暗黑主题覆盖
  - 完成时间: 2026-05-11

- [x] **战役预设系统**
  - D&D 5e「遗忘国度的阴影」
  - CoC 7th「阿卡姆谜案」
  - 修仙「青云问道」
  - 预设包含完整 systemPrompt、开场白、行动建议
  - 完成时间: 2026-05-11

- [x] **预设开场白**
  - 预设战役直接使用预设文本（非 AI 生成）
  - 自定义战役由 AI 生成开场
  - 对话下方显示行动建议 Chips
  - 完成时间: 2026-05-11

- [x] **思考窗口折叠/展开**
  - KP 思考过程显示在可折叠区域
  - 用户可选择展开查看或收起
  - 完成时间: 2026-05-11
  - ⚠ 2026-05-12 重构：移除可折叠面板，改为流式光标动画，思考内容直接显示在消息流中

- [x] **骰子公示增强**
  - 投骰结果全屏大字体动画展示
  - 成功/失败标记
  - 快捷投骰按钮（d4-d100）
  - 完成时间: 2026-05-11

- [x] **AI 配置完整 CRUD**
  - 创建、查看、编辑、删除 AI 配置
  - 激活/切换 AI 配置
  - API Key 编辑时可选留空保留原值
  - 完成时间: 2026-05-11

- [x] **聊天体验增强**
  - KP 消息 HTML 渲染（`<em>` 线索高亮）
  - GM 打字动画「正在编织世界」
  - 行动建议 Chips 上下文推导
  - 角色卡侧边栏（属性/技能/特质）
  - 完成时间: 2026-05-11
  - ⚠ 2026-05-12 重构：移除 GM 打字动画，改为 KP 消息末尾流式光标

- [x] **角色状态追踪** ⭐ 新增
  - AI KP 通过 `[CHAR_UPDATE: field=±delta]` 标记追踪角色状态变化
  - 支持 HP/AC/等级/六维属性 的增减
  - WebSocket 实时推送 `character_update` 到前端
  - 前端角色面板实时更新属性显示
  - 系统消息提示状态变化明细
  - 完成时间: 2026-05-12

- [x] **Dashboard 增强 & UI 中文化**
  - 新增「进行中的战役」概览区块
  - 战役卡片/列表添加删除按钮（Popconfirm 确认）
  - 删除战役级联删除存档和聊天记录
  - 属性标签中文化（STR→力量，DEX→敏捷 等）
  - 主题切换按钮中文化
  - 完成时间: 2026-05-12

---

## P0 — 核心体验（必须解决）✅ 已完成 (2026-05-15)

### 1. 角色卡数据注入 AI 上下文 🔥 ✅

**已完成 (2026-05-15):**
- `chat_session.py` GameState 新增 `selected_character` 字段，`set_selected_character()` 方法存储完整角色数据
- `get_full_system_prompt()` 注入角色完整信息（背景故事、性格特征、技能、装备）
- `chat.py` 新增 `select_character` WebSocket 消息处理，连接时自动注入角色数据
- `ChatRoom.tsx` 角色选择时通过 WebSocket 发送完整角色数据
- `websocket.ts` 新增 `selectCharacter()` 方法
- 快照方法 `get_game_snapshot()`/`load_from_snapshot()` 包含 `selected_character`

**问题：** 前端 ChatRoom 有角色选择下拉框，但选中角色后，角色的技能、背景故事、性格特质、装备等信息从不发送给 AI。AI 只知道 `character_name` 和 HP/AC/属性数字，不知道这个角色"是谁"、"会什么"、"性格如何"。这导致 AI KP 的回复千人一面，无法针对角色做出差异化叙事。

**怎么做：**

1. **后端 `chat_session.py`** — 新增方法 `set_selected_character(character_data: dict)`
   - 接收完整角色数据：name, race, character_class, level, backstory, personality, skills, attributes, hp, ac
   - 存入 `GameState.selected_character`
   - 修改 `get_full_system_prompt()`，将角色完整信息注入 system prompt：
     ```
     【当前玩家角色】
     姓名: xxx | 种族: xxx | 职业: xxx | 等级: xxx
     背景故事: xxx
     性格特征: xxx
     技能: xxx
     ```
   - 角色数据变化时（如 `CHAR_UPDATE` 触发），同步更新缓存

2. **后端 `chat.py`** — WebSocket 消息处理
   - 新增消息类型 `select_character`，前端选中角色时发送
   - `handle_player_message` 发送消息时，将选中角色的完整数据拼入消息上下文（或让 AI 从 system prompt 中读取）

3. **前端 `ChatRoom.tsx`** — 角色选择时触发
   - `handleSelectCharacter` 中通过 WebSocket 发送 `{type: "select_character", character_id: xxx}`
   - （可选）角色面板展示当前选中角色的完整信息

**改动范围：** `chat_session.py` + `chat.py` + `ChatRoom.tsx` + `websocket.ts`
**预计工时：** 小（~2h）

---

### 2. 存档恢复完整游戏状态 🔥 ✅

**已完成 (2026-05-15):**
- `chat.py` 新增 `save_game` WebSocket 消息处理，后端构建完整 `get_game_snapshot()`
- `handle_load_save` 增强：广播完整 NPC、场景、角色数据到前端
- `ChatRoom.tsx` 存档改为通过 WebSocket 发送，后端负责完整快照
- `websocket.ts` 新增 `sendSaveGame()` 方法
- `get_game_snapshot()`/`load_from_snapshot()` 包含 `selected_character`

**问题：** `ChatSession.get_game_snapshot()` 已经能捕获 NPC、地点、角色数据、消息数量等完整快照，但前端保存时只传了 `{campaign_id, session_number, messages_count}`（一个空壳）。加载存档时只恢复 `SessionLog` 里的历史消息，NPC 列表、当前场景、角色状态全部丢失。

**怎么做：**

1. **后端 `chat.py`** — 保存存档接口
   - 保存时调用 `session.get_game_snapshot()` 获取完整快照（已实现）
   - 将完整快照 `json.dumps` 存入 `Save.data` 字段
   - 检查 `Save` 模型是否有 `data` 字段（如无则新增 `data = Column(JSON)`）

2. **后端 `chat.py`** — 加载存档接口
   - 加载时从 `Save.data` 读取完整快照
   - 调用 `session.restore_from_snapshot(snapshot)`（已实现）
   - 恢复 NPC、地点、场景、角色状态
   - 广播 `save_loaded` 消息给前端

3. **前端 `ChatRoom.tsx`** — 保存/加载
   - 保存时收集更多上下文（当前场景描述等）
   - 加载时处理恢复的完整状态（更新角色面板、场景显示）

4. **后端 `chat_session.py`** — 快照增强
   - `get_game_snapshot()` 增加 `selected_character_id`、`current_scene`、`inventory_snapshot`
   - `restore_from_snapshot()` 完整恢复以上字段

**改动范围：** `chat.py` + `chat_session.py` + `models/save.py` + `ChatRoom.tsx`
**预计工时：** 中（~4h）

---

### 3. 记忆持久化（跨会话记忆） ✅

**已完成 (2026-05-15) — 短期方案:**
- `chat.py` `get_ai_response()` 中 `max_history` 从 20 提高到 50
- `load_messages_from_db()` 进入战役时自动加载所有历史消息到会话
- 前端重连时自动接收历史消息流

**问题：** 每次进入战役聊天，之前的对话记录会清空。AI KP 没有长期记忆，无法记住之前的剧情发展。

**怎么做：**

1. **短期方案（快速见效）：** 进入战役时自动加载最近 N 条（如 50 条）历史消息到会话上下文
   - 修改 `ChatSession.load_messages_from_db()`，加载后把历史消息注入 AI 的上下文窗口
   - 前端进入房间时显示历史消息列表（已有部分实现，需检查完整性）

2. **中期方案（推荐）：** Redis 存储会话状态
   - 使用 Redis Hash 存储 `session:{campaign_id}:{user_id}` → 完整 GameState JSON
   - 用户断开 WebSocket 时不销毁 session，保留 TTL（如 24 小时）
   - 重连时从 Redis 恢复完整会话状态
   - 使用 Redis List 存储消息历史（LRU 裁剪）

3. **长期方案：** 迁移到 PostgreSQL
   - 利用 PostgreSQL JSONB 存储会话状态
   - 更丰富的查询能力（按时间/章节检索历史）
   - 数据持久化更可靠

**改动范围：** `chat.py` + `chat_session.py` + 新增 Redis 集成
**预计工时：** 短期 2h / 中期 8h / 长期 16h

---

### 4. 随时聊天的分支对话 💬 ✅

**已完成 (2026-05-15):**
- 新增 `models/chat_branch.py` — ChatBranch 数据模型
- `models/save.py` SessionLog 新增 `branch_id` 字段
- `chat_session.py` ChatSession 新增分支管理（`create_branch`/`switch_to_branch`/`merge_branch_summary`）
- `chat.py` 新增 `branch_create`/`branch_switch`/`branch_list` WebSocket 处理
- `ChatRoom.tsx` 分支 UI：分支选择器、创建分支 Modal、消息 Fork 按钮、分支消息视觉区分
- `websocket.ts` 新增 `createBranch()`/`switchBranch()`/`listBranches()` 方法
- 分支 AI 上下文：注入主线分叉点上下文，分支间消息隔离

**问题：** 希望每次的游戏进程可以有随时聊天的**分支**，分支随意和 AI 聊天不影响主线流程，切回主线时继续对话可以有分支对话的记忆作为上下文。

**怎么做：**

1. **数据模型** — 新增 `ChatBranch` 表
   ```
   ChatBranch {
     id, campaign_id, parent_message_id,  // parent_message_id 标记分支起点
     name, created_at, is_active
   }
   ```
   - `SessionLog` 新增 `branch_id` 字段（nullable，null = 主线）
   - 分支从主线某条消息处 fork，分支内的消息独立存储

2. **后端 `chat.py`** — 分支操作
   - `create_branch`: 从当前消息创建分支，复制当前会话状态到分支
   - `switch_branch`: 切换到指定分支，保存当前分支的消息记录，加载目标分支的消息和状态
   - `merge_branch`: （可选）将分支摘要合并回主线作为上下文记忆
   - WebSocket 消息类型: `branch_create`, `branch_switch`, `branch_list`

3. **前端 `ChatRoom.tsx`** — 分支 UI
   - 消息旁添加「分支」按钮，点击从该消息处创建分支
   - 顶部或侧边栏显示分支列表（主线 + 分支1 + 分支2...）
   - 切换分支时清空当前消息列表，加载目标分支的消息
   - 视觉上区分主线/分支（如分支用不同颜色边框）

4. **AI 上下文处理**
   - 分支内的 AI 请求携带分支起点之前的完整主线对话作为上下文
   - 分支间的对话互相隔离
   - 切换回主线时，可选地将当前分支生成摘要注入主线 AI 上下文

**改动范围：** 新模型 `ChatBranch` + `chat.py` + `chat_session.py` + `ChatRoom.tsx` + `websocket.ts`
**预计工时：** 大（~12h）

---

### 5. 当前已知问题的快速修复 🛠

**问题清单：**

- [ ] **角色卡选中后 AI 不知道角色信息**（见 P0-1）
- [ ] **存档只保存消息数量，不保存游戏状态**（见 P0-2）
- [ ] **AI 对话历史在刷新/重进后丢失**（见 P0-3）
- [ ] **投骰结果只在聊天显示，不触发任何游戏机制**
- [ ] **预设战役的 systemPrompt 中引用了角色属性，但角色未选时属性全是 0**

---

- [x] **UI/UX 精细化修复** ⭐ 新增
  - KP 统一称呼（GM → KP）
  - 分支对话 AI 人设独立（轻松闲聊风格、流式输出）
  - 主线 KP 回复精炼化（每块2-4句、整体300字以内、直击重点）
  - 角色身份被 AI 正确识别（系统提示词强调角色是谁、预设剧本去硬编码角色名）
  - 左侧面板新增背包栏（装备/道具展示，Character 模型新增 equipment JSON 字段）
  - 完成时间: 2026-05-15

- [x] **WebSocket 消息重复修复**
  - 根因: React Strict Mode 双重挂载导致两条 WebSocket 连接同时活跃
  - 修复: `websocket.ts` connect()/disconnect() 中设置 `onclose=null` 阻止重连竞态
  - 完成时间: 2026-05-15

- [x] **战役删除 Bug 修复**
  - 根因: SQLAlchemy ORM backref 尝试 `SET NULL` 到 `chat_branches.campaign_id`（NOT NULL 列）
  - 修复: `campaigns.py` 改用纯 SQL bulk delete，按外键依赖顺序删除（SessionLog → ChatBranch → Save → Campaign）
  - 完成时间: 2026-05-15

- [x] **战役时间显示与排序**
  - Campaign 模型新增 `last_played_at` 字段，WebSocket 连接时自动更新
  - Dashboard 显示创建时间和上次游玩时间
  - 战役列表按 `updated_at desc` 排序
  - 完成时间: 2026-05-15

---

## P1 — 用户体验优化

### 6. 战斗判定接入聊天流 ⚔️

**问题：** `services/dice.py` 有完整的 D&D 5e 规则（攻击掷骰、豁免、技能检定、优劣势、先攻），但聊天里玩家说"我攻击哥布林"完全靠 AI 自由发挥描述。没有自动 AC 比对、命中判定、伤害掷骰。战斗是纯叙事，没有 TRPG 的机械感。

**怎么做：**

1. **意图检测层** — `services/dice.py` 新增 `detect_combat_intent(message: str) -> CombatAction | None`
   - 用正则或简单 NLP 检测攻击意图关键词（"攻击"、"砍"、"射"、"施法"、"擒抱" 等）
   - 提取目标（"哥布林"、"巨龙"）
   - 提取武器/法术类型（"长剑"、"火球术"）
   - 返回结构化的 `CombatAction(action_type, target, weapon, modifiers)`

2. **判定引擎** — `services/dice.py` 新增 `resolve_combat(action: CombatAction, character: Character) -> CombatResult`
   - 根据武器类型确定掷骰（d20 + 熟练加值 + 力量/敏捷调整值）
   - 比对目标 AC（从 AI 返回或 DM 预设的 NPC 数据中获取）
   - 命中后掷伤害骰（武器伤害 + 属性调整值）
   - 暴击处理（nat 20）和大失败（nat 1）
   - 返回 `CombatResult(hit, damage, roll_detail, narrative)`

3. **流程集成** — 修改 `chat.py` 消息处理
   ```
   玩家消息 → detect_combat_intent → (如果有攻击意图)
     → resolve_combat → 生成判定描述
     → 将判定结果注入 AI 上下文（AI 据此叙事）
     → 广播 dice_result + 战斗描述
     → 应用 CHAR_UPDATE（HP 减少等）
   ```

4. **先攻追踪** — `GameState` 新增 `initiative_order: list`
   - AI 可声明 `[INITIATIVE: 玩家 18, 哥布林 12, 兽人 7]`
   - 前端显示先攻顺序条
   - 自动推进回合

5. **NPC 数据管理** — `GameState` 的 `npcs` 增强
   - 每个 NPC 可记录: name, ac, hp, attacks, abilities
   - AI 可通过标记声明 NPC 数据: `[NPC: 哥布林, AC=15, HP=7, ATK=短剑+4(1d6+2)]`
   - KP 可在战役设置中预定义 NPC 模板

**改动范围：** `services/dice.py` + `chat.py` + `chat_session.py` + `ChatRoom.tsx`
**预计工时：** 大（~10h）

---

### 7. 角色卡预设模板

- [ ] 添加多个预设人设（如：战士、法师、盗贼、猎人等）
- [ ] 随机生成角色（种族+年龄+职业+背景）
- [ ] 关联issue: #3

**怎么做：**
1. 在 `frontend/src/data/presets.ts` 中新增 `CHARACTER_PRESETS` 数组
2. 每个预设包含：name, race, character_class, backstory, personality, attributes, skills, hp, ac
3. Dashboard 创建角色时显示预设模板卡片，点击自动填充表单
4. 随机生成：用种子随机组合种族/职业/背景/性格，调用 AI 生成 backstory

---

### 8. 人设扩展

- [ ] 添加性格特征（MBTI/大五人格简化版）
- [ ] 添加SAN值（理智值）状态
- [ ] 关联issue: #4

**怎么做：**
1. `Character` 模型新增字段：`personality_type`（MBTI 如 "INTJ"）、`san_current`、`san_max`
2. 角色创建表单新增性格选择和 SAN 值滑块
3. SAN 值影响 AI KP 的描述风格（低 SAN 时增加恐怖/幻觉元素）
4. 角色面板展示性格标签和 SAN 值进度条

---

## P2 — 世界构建系统 ⭐

### 9. 场景/地图系统

**功能描述：**
- KP 可上传图片作为战役地图（.jpg/.png）
- 地图上可标记多个区域（房间、地点）
- 玩家可查看地图并选择移动到不同区域
- 区域触发事件和剧情

**怎么做：**

1. **后端模型** — `models/map.py`
   ```
   Map { id, campaign_id, name, image_url, width, height }
   MapRegion { id, map_id, name, x, y, width, height, description, is_locked, is_hidden }
   PlayerPosition { id, session_id, character_id, map_id, region_id, x, y }
   ```

2. **后端路由** — `routers/map.py`
   - CRUD: 上传地图、创建/编辑/删除区域、查询地图数据
   - WebSocket 同步：玩家移动时广播位置更新

3. **前端组件** — `MapView.tsx`
   - 左侧：地图展示（可缩放、拖拽，使用 CSS transform 或 canvas）
   - 右侧：区域信息面板
   - 底部：位置切换按钮
   - 其他玩家位置标记（P3 多人时用）

4. **触发机制**
   - 进入某区域 → 自动推送区域描述
   - 特定区域 → 触发剧情事件（调用 AI 生成）
   - 踩陷阱/搜索 → 自动投骰判定

**预计工时：** 大（~16h）

---

### 10. 物品/背包系统 🎒

**功能描述：**
- 每个角色拥有独立背包
- 物品分类（武器、防具、消耗品、任务道具）
- 物品使用/丢弃/交易
- 关键道具自动记录到剧情

**怎么做：**

1. **后端模型** — `models/item.py`
   ```
   Item { id, name, type, rarity, description, effect, icon_url, is_consumable }
   CharacterInventory { id, character_id, item_id, quantity, is_equipped, acquired_at, acquired_way }
   ```

2. **后端路由** — `routers/inventory.py`
   - CRUD: 获取背包、添加物品、使用物品、丢弃物品、装备/卸下
   - 物品效果应用：属性加成、投骰加成、恢复 HP 等

3. **物品效果类型**
   - 属性加成（力量+2）→ 直接修改 `character.attributes`
   - 投骰加成（对判定+5）→ 注入 AI 上下文
   - 一次性使用（药水）→ 使用后数量-1，效果生效
   - 剧情钥匙（触发特定事件）→ AI 检测到该物品时解锁剧情分支

4. **前端 UI**
   - 角色面板新增「背包」Tab（与属性/战斗数据并列）
   - 物品卡片展示（图标、名称、数量）
   - 装备/使用按钮
   - 拖拽装备到快捷栏

5. **AI 集成**
   - 背包内容注入 system prompt，AI 知道玩家有哪些物品
   - AI 可通过 `[ITEM_USE: 治疗药水]` 提示玩家使用物品
   - 战利品掉落：战斗后 AI 通过 `[LOOT: 短剑, 金币+50]` 发放物品

**预计工时：** 大（~12h）

---

### 11. 玩家位置同步（P3 多人前置）

**功能描述：**
- WebSocket 实时同步所有玩家位置
- 在地图上显示所有玩家图标
- 位置变化时通知所有玩家
- KP 可传送/踢出玩家

---

## P3 — 多人游戏

- [ ] **AI 队友模式**
  - 支持用户+AI 队友双人跑团
  - AI 队友根据角色卡性格自主行动
  - 关联issue: #5

- [ ] **多人实时跑团**
  - Campaign 支持多用户（DM + 多名玩家）
  - 邀请码/链接加入战役
  - DM 权限：控制 NPC、地图、剧情
  - 玩家权限：控制自己角色、查看公开信息
  - WebSocket 房间广播所有玩家动作

---

## P4 — 智能增强

- [ ] **用户画像分析**
  - 抽取用户行为逻辑
  - 分析玩家性格特征（激进/保守/探索型等）
  - KP 根据用户性格调整剧情难度和风格
  - 关联issue: #6

---

## P5 — 内容创作工具

- [ ] **AI 剧本生成器**
  - 输入关键词/类型，自动生成剧本框架
  - 生成 NPC 性格、场景描述、剧情分支
  - 导出为可编辑剧本

---

## 技术债务

- [ ] 添加单元测试
- [ ] API 限流保护
- [ ] WebSocket 重连优化
- [ ] 数据库索引优化
- [ ] 前端错误边界（Error Boundary）
- [ ] AI 请求超时处理优化

---

## 推荐 Skill（可加速开发）

| 任务 | 推荐 Skill | 安装命令 |
|------|-----------|----------|
| Redis 集成 | `redis/agent-skills@redis-development` | `npx skills add redis/agent-skills@redis-development -g -y` |
| 后端测试 | `supercent-io/skills-template@backend-testing` | `npx skills add supercent-io/skills-template@backend-testing -g -y` |
| WebApp 测试 | `anthropics/skills@webapp-testing` | `npx skills add anthropics/skills@webapp-testing -g -y` |

---

## 优先级建议

| 优先级 | 功能 | 理由 | 预计工时 |
|--------|------|------|----------|
| **P0** | 角色卡数据注入 AI 上下文 | 让 AI 认识角色，回复质量立竿见影 | ~2h |
| **P0** | 存档恢复完整游戏状态 | 已半实现，接上线即可，解决数据丢失 | ~4h |
| **P0** | 记忆持久化（短期） | 刷新/重进后对话不丢失 | ~2h |
| **P0** | 随时聊天分支对话 | 差异化体验，solo 跑团核心需求 | ~12h |
| P1 | 战斗判定接入聊天流 | 从纯叙事变成有规则的游戏 | ~10h |
| P1 | 角色卡预设模板 | 降低新用户门槛 | ~4h |
| P1 | 人设扩展（SAN值等） | CoC 剧本必备 | ~3h |
| P2 | 物品/背包系统 | RPG 核心系统，增加深度 | ~12h |
| P2 | 场景/地图系统 | 世界构建核心，带来沉浸感 | ~16h |
| P2 | AI 队友 | 差异化竞争点 | ~16h |
| P4 | 用户画像 | 长期智能化的基础 | ~24h |
