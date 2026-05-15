# 修改记录

## 2026-05-15 — P0 核心体验开发

### P0-1: 角色卡数据注入 AI 上下文
**后端：**
- `chat_session.py` — GameState 新增 `selected_character` 字段；新增 `set_selected_character()` 方法存储完整角色数据（背景故事、性格、技能、装备）；`get_full_system_prompt()` 注入角色完整信息区段；`get_game_snapshot()`/`load_from_snapshot()` 包含 `selected_character`
- `chat.py` — 新增 `select_character` WebSocket 消息处理 (`handle_select_character`)；WebSocket 连接时自动将用户角色完整数据注入会话

**前端：**
- `websocket.ts` — 新增 `selectCharacter()` 方法
- `ChatRoom.tsx` — 角色 Select onChange 通过 WebSocket 发送完整角色数据

### P0-2: 存档恢复完整游戏状态
**后端：**
- `chat.py` — 新增 `save_game` WebSocket 消息处理 (`handle_save_game`)，后端调用 `get_game_snapshot()` 构建完整快照并存入 Save；`handle_load_save` 增强：广播 NPC、场景、角色数据、selected_character 到前端；新增 `datetime` 导入
- `chat_session.py` — `get_game_snapshot()`/`load_from_snapshot()` 包含 `selected_character`

**前端：**
- `websocket.ts` — 新增 `sendSaveGame()` 方法
- `ChatRoom.tsx` — `handleSaveGame` 改为通过 WebSocket 发送存档请求；`handleOnMessage` 处理 `save_loaded` 增强数据（角色状态恢复、selected_character 恢复）；处理 `save_created` 消息刷新存档列表

### P0-3: 记忆持久化（短期方案）
**后端：**
- `chat.py` — `get_ai_response()` 中 `max_history` 从 20 提高到 50

### P0-4: 随时聊天的分支对话
**后端：**
- 新增 `models/chat_branch.py` — ChatBranch 模型（id, campaign_id, parent_message_id, name, is_active, created_at）
- `models/save.py` — SessionLog 新增 `branch_id` 字段和 ChatBranch relationship；导入 ChatBranch
- `main.py` — 注册 ChatBranch 模型
- `chat_session.py` — ChatSession 新增 `current_branch_id`、`branch_messages`、`branch_parent_context`；新增 `create_branch()` 从指定消息 fork；`switch_to_branch()` 切换分支消息列表；`get_messages_for_ai()` 增强注入分支上下文；`merge_branch_summary()` 合并分支摘要回主线
- `chat.py` — 新增 `handle_branch_create`/`handle_branch_switch`/`handle_branch_list`/`_broadcast_branch_list`；SessionLog 保存时包含 `branch_id`

**前端：**
- `websocket.ts` — ChatMessage 类型扩展（branch_list, branch_created, branch_switched, branches 等）；新增 `createBranch()`/`switchBranch()`/`listBranches()` 方法
- `ChatRoom.tsx` — 新增分支状态（branches, currentBranchId, branchModalVisible, branchName）；分支选择器（Select 切换主线/分支）；创建分支 Modal；KP 消息 Fork 按钮；分支消息视觉区分（branch-tag、左侧色条）；`handleOnMessage` 处理 branch_list/branch_created/branch_switched
- `ChatRoom.css` — 新增分支相关样式（分支选择器、分支标签、分支消息色条、Fork 按钮悬停效果）

### 影响范围
| 层级 | 文件 | 变更类型 |
|------|------|----------|
| Backend | `services/chat_session.py` | 增强（完整角色数据 + 分支管理） |
| Backend | `routers/chat.py` | 新增（角色选择/存档/分支处理） |
| Backend | `models/chat_branch.py` | 新增（分支模型） |
| Backend | `models/save.py` | 增强（branch_id） |
| Backend | `main.py` | 增强（模型注册） |
| Frontend | `services/websocket.ts` | 增强（类型 + 方法扩展） |
| Frontend | `pages/ChatRoom.tsx` | 增强（角色选择 + 存档 + 分支 UI） |
| Frontend | `pages/ChatRoom.css` | 增强（分支样式） |

---

## 2026-05-12 — 角色状态追踪 & UI 打磨

### 角色状态追踪系统

**后端：**
- `chat_session.py` — GameState 新增 `character_stats` 字段；新增 `set_character_stats()` 方法；`get_full_system_prompt()` 注入角色当前状态和 `[CHAR_UPDATE:]` 标记规则；新增 `parse_character_updates()` 静态方法解析 AI 响应中的状态变化标记
- `chat.py` — WebSocket 连接时加载用户角色数据到会话缓存；AI 响应完成后解析 `[CHAR_UPDATE: field=±delta]` 标记，应用到数据库角色并广播 `character_update` 消息到前端
- `campaigns.py` — 删除战役时级联删除关联的存档和聊天记录

**前端：**
- `websocket.ts` — ChatMessage 新增 `character_update` 类型和 `updates`/`stats` 字段
- `ChatRoom.tsx` — 处理 `character_update` 消息，更新角色面板属性显示，系统消息提示状态变化

### UI 打磨

- **ChatRoom** — 移除可折叠思考面板，改为 KP 消息末尾流式光标动画；属性标签中文化（STR→力量 等）；移除"GM 编织世界"打字指示器
- **Dashboard** — 新增「进行中的战役」概览区块；战役卡片添加删除按钮（Popconfirm 确认）；属性标签中文化（HP→生命，AC→护甲）；主题切换按钮中文化
- **CSS** — 清理思考面板相关样式，新增流式光标动画，新增活跃战役列表样式

### 影响范围

| 层级 | 文件 | 变更类型 |
|------|------|----------|
| Backend | `routers/campaigns.py` | 增强（级联删除） |
| Backend | `routers/chat.py` | 新增（状态追踪） |
| Backend | `services/chat_session.py` | 新增（状态解析） |
| Frontend | `services/websocket.ts` | 增强（类型扩展） |
| Frontend | `pages/ChatRoom.tsx` | 重构（UI 简化） |
| Frontend | `pages/ChatRoom.css` | 重构（样式清理） |
| Frontend | `pages/Dashboard.tsx` | 新增（删除/概览） |
| Frontend | `pages/Dashboard.css` | 新增（列表样式） |
