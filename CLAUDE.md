# Tabletop Agent (暗幕 Anmu)

TRPG AI KP 跑团平台 — FastAPI + React + MySQL + WebSocket 实时聊天

## 技术栈

| 层 | 技术 |
|---|------|
| Backend | FastAPI (Python), SQLAlchemy ORM, MySQL, WebSocket, JWT auth |
| Frontend | React 19, TypeScript, Vite 8, Ant Design 6, Zustand 5, React Router 7 |
| AI | DeepSeek / Claude / MiniMax 多 Provider，统一 AIGateway 调度 |
| 样式 | OKLCH 色彩空间暗黑主题，Grimoire 风格 |

## 启动命令

```bash
# Backend (端口 8000)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (端口 5173)
cd frontend
npm install
npm run dev
```

⚠ Windows 上 uvicorn `--reload` 有时检测不到文件变更，改完代码没生效就 `taskkill /F /IM python.exe` 然后重启。

## 项目结构

```
helloGolang/
├── backend/
│   ├── main.py                  # FastAPI 入口，注册模型+挂载路由，CORS localhost:5173
│   ├── config.py                # .env Settings (DB URL, JWT secret, API prefix)
│   ├── database.py              # SQLAlchemy engine, session, get_db 依赖
│   ├── models/                  # ORM 模型 (6表)
│   │   ├── user.py              # User (users)
│   │   ├── ai_config.py         # AIConfig + AIProvider enum (ai_configs)
│   │   ├── character.py         # Character + JSON字段 attributes/skills/equipment/personality
│   │   ├── campaign.py          # Campaign + CampaignStatus enum (active/archived)
│   │   ├── chat_branch.py       # ChatBranch (对话分支)
│   │   └── save.py              # Save (snapshot JSON) + SessionLog
│   ├── routers/
│   │   ├── auth.py              # /api/auth — register, login, me (JWT)
│   │   ├── ai_configs.py        # /api/ai-configs — CRUD + activate
│   │   ├── campaigns.py         # /api/campaigns — CRUD, 纯SQL级联删除, updated_at排序
│   │   ├── characters.py        # /api/characters — CRUD + AI生成
│   │   ├── saves.py             # /api/saves — 存档/读档 + session logs
│   │   └── chat.py              # WebSocket /ws/chat/{campaign_id} — 核心游戏循环
│   ├── services/
│   │   ├── ai_gateway.py        # 多Provider统一接口 (DeepSeek/Claude/MiniMax), chat_stream流式
│   │   ├── chat_session.py      # ChatSession 内存管理, GameState, 分支管理, system prompt构建
│   │   ├── character_generator.py # AI角色卡生成 (JSON解析)
│   │   └── dice.py              # D&D骰子系统 (NdX, 优劣势, 技能检定, parse_dice_command)
│   ├── schemas/                 # Pydantic 请求/响应模型
│   └── utils/security.py        # bcrypt, JWT create/verify, get_current_user 依赖
├── frontend/src/
│   ├── App.tsx                  # 路由: /login, /register, / (Dashboard), /chat/:campaignId
│   ├── pages/
│   │   ├── Login.tsx / Register.tsx  # 登录注册
│   │   ├── Dashboard.tsx        # 主面板 — 概览/战役/角色/AI配置 四个Tab
│   │   └── ChatRoom.tsx         # 游戏房间 — 聊天/角色面板/骰子/存档/分支
│   ├── components/
│   │   └── CharacterModal.tsx   # 角色卡完整表单 (全字段CRUD + 职业预设 + 购点系统)
│   ├── services/
│   │   ├── api.ts               # Axios HTTP (authAPI, aiConfigAPI, characterAPI, campaignAPI, saveAPI)
│   │   └── websocket.ts         # WebSocket 客户端, 20+消息类型, 自动重连防竞态
│   ├── stores/useAuthStore.ts   # Zustand 认证状态
│   ├── hooks/useTheme.ts        # 暗黑/亮色主题切换 (localStorage + 系统偏好)
│   ├── data/
│   │   ├── presets.ts           # 3个预设剧本 (D&D/CoC/修仙) — systemPrompt + 开场白 + 建议
│   │   └── classPresets.ts      # 10个职业预设 — 基础属性 + 购点 + 默认装备/技能 JSON驱动
├── TODO.md                      # 开发待办清单 (P0-P5)
├── CHANGES.md                   # 详细变更记录
└── CLAUDE.md                    # 本文件 — 新会话快速上下文
```

## 数据库

MySQL `tabletop_agent`，6张核心表：users → ai_configs, characters, campaigns → saves, session_logs, chat_branches

Character 的 `equipment` 和 `attributes` 是 JSON 列。Campaign 的 `last_played_at` 可空。

## 关键约定

- **称呼**: 统一用 **KP**（不是 GM/DM）
- **分支对话**: 叫"闲聊"，AI persona 是"冒险伙伴"（用"我"自称、口语化），不是正式 KP
- **主线 AI**: 每块 2-4 句，整体 300 字以内
- **主题色**: `oklch(65% 0.16 35)` 琥珀金 accent
- **CSS 变量**: 在 `src/styles/themes.css` 定义，OKLCH 色彩空间
- **字体**: `--font-display` (标题), `--font-body` (正文), `--font-mono` (数据)
- **角色身份**: system prompt 强调"你就是这个角色"，不硬编码预设角色名到剧本
- **背包**: `Character.equipment` JSON 数组，前端左侧面板展示

## WebSocket 消息类型 (chat.py)

核心类型: `player_message`, `kp_thinking`, `kp_thinking_chunk`, `kp_response`
分支: `branch_create`, `branch_message`, `branch_kp_thinking`, `branch_kp_thinking_chunk`, `branch_kp_response`
游戏: `roll_dice`, `dice_result`, `character_update`, `select_character`, `save_game`, `save_loaded`, `opening_story`, `suggestions`
AI 输出格式: `[DESC]` `[ACTION]` `[NPC]` `[EVENT]` `[STATUS]` `[SUGGESTIONS:...]` `[CHAR_UPDATE: field=±delta]`

## 已知坑

1. **React Strict Mode 双重挂载** → WebSocket 两条连接。修复: connect()/disconnect() 中 `ws.onclose=null` 阻止重连竞态
2. **ORM backref cascade** → 删除 Campaign 时 SET NULL 到 NOT NULL 列报错。修复: 用纯 SQL bulk delete，按外键依赖顺序 (SessionLog→ChatBranch→Save→Campaign)
3. **Windows uvicorn reload** → 经常检测不到文件变更，直接 taskkill 重启
4. **Edit 工具匹配中文** → 中文+tab 混排的字符串经常匹配失败，用 Write 工具重写整个文件或找唯一 ASCII 片段匹配
5. **分支 AI 太正式** → 根因是 main_history 作为 conversation messages 注入，AI 模仿主线 KP。修复: 改为 system reference 注入，明确标注"[主线KP]"和"[玩家]"
6. **分支 AI 幻觉** → 预设开场白是客户端 only，后端 session.messages 为空，snapshot 缺少对话。修复: 前端 createBranch 时传 messages，后端 build_context_snapshot 用 frontend_messages 优先，snapshot 含完整角色 JSON + 世界设定

## 当前进度 (2026-05-16)

### ✅ 已完成
- P0-1 角色卡数据注入 AI 上下文
- P0-2 存档恢复完整游戏状态
- P0-3 记忆持久化 (短期: max_history=50, 自动加载历史)
- P0-4 分支对话 ChatBranch + 闲聊人设 + 流式输出
- **分支上下文快照** — 创建分支时生成完整 JSON (角色全部属性/装备/技能/人格/目标/关系 + 世界状态/NPC/任务/对话摘要/世界设定)，存入 DB，分支 AI 引用快照杜绝幻觉
- **角色 CRUD 完整** — CharacterModal 组件，全部字段可编辑，增删改查
- **职业预设 + 购点系统** — 10 种预设 (战士/法师/盗贼/牧师/游侠/吟游诗人/德鲁伊/圣骑士/术士/学生)，基础属性 30 + 6 可分配点数，默认装备+技能，JSON 驱动
- **骰子 & 规则引擎** — D&D 5e NdX/优劣势/技能检定/先攻，动作命令 /attack /skill /cast /use，判定结果注入 AI 叙事
- **结构化记忆** — GameState 扩展: NPC/任务/地点/关系网/世界状态/战斗状态，get_memory_prompt() 摘要
- 角色状态追踪 [CHAR_UPDATE]
- UI/UX: KP统一称呼, 主线精简, 角色身份, 背包栏, 战役时间显示
- 预设剧本 (D&D/CoC/修仙) + 去硬编码角色名
- 暗黑主题 + OKLCH + 中文化
- **标签系统移除** — [DESC][ACTION][NPC][EVENT][STATUS] 替换为 **bold** 内联强调
- 战役与角色一对一绑定，创建时选择，游戏中不可切换
- Redis 会话持久化 (SessionStore)，优雅降级
- PostgreSQL 支持

### 📋 待开发 (P1-P2)
- 战斗中自动识别攻击意图，前端战斗 UI (先攻条/敌人HP/回合推进)
- SAN 值系统 (CoC)
- 地图系统 (图片+区域标记+触发)
- 完整物品系统 (分类/使用/交易/效果)

详见 TODO.md
