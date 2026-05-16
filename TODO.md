# Tabletop Agent (暗幕 Anmu) — 开发待办

---

## ✅ 已完成

### 核心架构
- [x] FastAPI + React + MySQL + WebSocket 实时聊天
- [x] JWT 认证（register / login / me）
- [x] AI 多 Provider 统一调度（DeepSeek / Claude / MiniMax），流式输出
- [x] 暗黑主题（OKLCH 色彩空间），Grimoire 风格 UI
- [x] 称呼统一为 **KP**（非 GM/DM）

### 角色系统
- [x] 角色 CRUD + AI 生成角色卡
- [x] 角色完整数据注入 AI 上下文（背景故事、性格、技能、装备）
- [x] 角色状态追踪 `[CHAR_UPDATE: field=±delta]`，WebSocket 实时同步前端
- [x] 角色个性化扩展 — relationships、faction、goals、ideals、flaws、personal_traits
- [x] AI system prompt 角色驱动叙事（背景/性格/关系/装备影响 NPC 反应）
- [x] 角色状态变化后自动同步 selected_character 缓存
- [x] `get_character_summary()` / `get_character_state_text()` 辅助方法
- [x] 左侧面板：属性 + 技能 + 背包 + 特质展示
- [x] 属性标签中文化（STR→力量，DEX→敏捷 等）

### 战役系统
- [x] 战役 CRUD + 纯 SQL 级联删除（SessionLog → ChatBranch → Save → Campaign）
- [x] 3 套预设剧本（D&D / CoC / 修仙），含 systemPrompt + 开场白 + 行动建议
- [x] 预设剧本去硬编码角色名
- [x] 自定义战役 AI 生成开场
- [x] 战役时间追踪（created_at / last_played_at / updated_at 排序）
- [x] Dashboard 概览区块 + 删除按钮

### 对话系统
- [x] WebSocket 实时聊天，20+ 消息类型
- [x] 主线 KP 精炼约束（每块 2-4 句，整体 300 字以内）
- [x] 分支对话（闲聊）— 独立 casual persona，流式输出，主线记忆注入
- [x] 分支 UI：创建/切换/消息区分/Fork 按钮
- [x] 流式光标动画
- [x] 行动建议 Chips（从 AI 响应解析 `[SUGGESTIONS: ...]`）

### 骰子 & 规则引擎
- [x] D&D 5e 骰子系统（NdX / 优劣势 / 技能检定 / 先攻）
- [x] 骰子结果大字体动画展示
- [x] 快捷投骰按钮（d4-d100）
- [x] 规则判定引擎：`calculate_ac()` / `resolve_attack()` / `resolve_skill_check()` / `resolve_saving_throw()` / `apply_condition()`
- [x] 动作命令解析：`/attack` `/skill` `/cast` `/use` + 自然语言检测
- [x] 判定结果注入 AI 叙事上下文（后端判定 → AI 描述）

### 结构化记忆
- [x] GameState 扩展：quests / world_state / relationship_map / 结构化 NPC / 结构化 locations
- [x] 战斗状态追踪：combat_state / enemies / turn_order / initiative
- [x] `get_memory_prompt()` — 结构化记忆摘要（NPC/任务/地点/关系/世界状态/战斗）
- [x] AI 请求优化：记忆摘要 + system prompt + 判定结果 + 20 条精简历史

### 存档系统
- [x] 完整游戏快照（场景/NPC/任务/战斗/世界状态/角色/分支）
- [x] 存档自动生成丰富摘要（场景 + 角色 + 任务 + 战斗状态）
- [x] 加载时完整恢复世界状态（含 branch_id / combat_state）
- [x] 前端存档预览：角色名、场景、战斗标识、任务数
- [x] SessionLog 持久化消息历史

### 私有部署
- [x] PostgreSQL 支持（`DATABASE_URL` 兼容 mysql/postgresql）
- [x] Redis 会话持久化（`SessionStore`，优雅降级）
- [x] WebSocket 连接恢复 Redis 会话，断开自动保存
- [x] `.env.example` 配置模板

### Bug 修复
- [x] WebSocket React Strict Mode 双重连接竞态
- [x] ORM backref cascade 删除战役报错（改用纯 SQL）
- [x] 分支 AI 口吻太正式（主线历史改为 system reference 注入）
- [x] 分支 AI 幻觉 — 上下文快照系统（完整角色 JSON + 世界设定 + 对话摘要 + 反幻觉铁律）
- [x] 行动建议消失 — 移除 kp_response 角色校验，presetSuggestionsRef 兜底
- [x] 标签系统彻底清理 — [DESC][ACTION] 等替换为 **bold**，移除 CSS 彩色块样式
- [x] Windows uvicorn reload 检测不到文件变更

### 角色卡系统
- [x] 角色 CRUD 完整 — CharacterModal 组件，全部字段可编辑
- [x] 职业预设系统 — 10 种预设（战士/法师/盗贼/牧师/游侠/吟游诗人/德鲁伊/圣骑士/术士/学生）
- [x] 购点系统 — 基础属性 sum=30 + 6 自由分配点数，JSON 驱动
- [x] 每职业默认装备 1-2 个、默认技能 1 个、不同基础属性
- [x] 战役-角色一对一绑定，创建战役时选定，游戏中不可切换

### 骰子 & 规则引擎
- [x] D&D 5e 骰子系统（NdX/优劣势/技能检定/先攻/AC命中/伤害）
- [x] 动作命令解析：/attack /skill /cast /use + 自然语言检测
- [x] 判定结果注入 AI 叙事上下文（后端判定 → AI 描述）

---

## P1 — 当前重点

### 战斗判定接入聊天流
- [ ] 战斗中自动识别攻击意图，调用规则引擎
- [ ] 前端战斗界面：先攻条、敌人 HP 显示、回合推进
- [ ] NPC 数据管理（AC/HP/攻击），AI 通过标记声明 `[NPC: ...]`
- [ ] 战斗状态前端可视化

### 人设扩展
- [ ] SAN 值系统（CoC 剧本核心）
- [ ] 性格类型标签（MBTI 简化版）
- [ ] 低 SAN 时 AI 描述风格变化（恐怖/幻觉元素）

---

## P2 — 世界构建系统

### 场景 / 地图
- [ ] KP 上传地图图片，标记区域（房间/地点）
- [ ] 玩家查看地图、选择移动到不同区域
- [ ] 区域触发事件和剧情（进入时自动推送描述）
- [ ] 踩陷阱/搜索自动投骰判定

### 物品 / 背包系统
- [ ] 物品分类（武器/防具/消耗品/任务道具）
- [ ] 物品使用/丢弃/交易，装备/卸下
- [ ] 物品效果应用（属性加成、投骰加成、恢复 HP）
- [ ] 战利品掉落 `[LOOT: ...]`
- [ ] AI 感知背包内容，可通过 `[ITEM_USE: ...]` 提示玩家

---

## P3 — 多人游戏

- [ ] AI 队友模式（双人跑团，AI 队友自主行动）
- [ ] 多人实时跑团（DM + 多名玩家）
- [ ] 邀请码/链接加入战役
- [ ] DM 权限：控制 NPC/地图/剧情
- [ ] 玩家位置实时同步

---

## P4 — 智能增强

- [ ] 用户画像分析（激进/保守/探索型）
- [ ] KP 根据玩家性格调整剧情难度和风格

---

## P5 — 内容创作工具

- [ ] AI 剧本生成器（关键词 → 剧本框架 + NPC + 场景 + 分支）
- [ ] 导出为可编辑剧本

---

## 技术债务

- [ ] 单元测试（backend + frontend）
- [ ] API 限流保护
- [ ] WebSocket 重连优化（指数退避）
- [ ] 数据库索引优化
- [ ] 前端 Error Boundary
- [ ] AI 请求超时处理优化
- [ ] 数据库迁移脚本（Alembic）
