# Tabletop Agent — 暗幕

TRPG（桌面角色扮演游戏）AI KP（主持人）助手，基于 Web 的实时跑团平台。

## 功能

- **用户系统** - 注册、登录、JWT 认证
- **战役管理** - 创建战役（支持预设剧本 D&D 5e / CoC 7th / 修仙），自定义剧本
- **AI KP** - 支持 DeepSeek / Claude / MiniMax 等大模型，可切换激活
- **实时聊天** - WebSocket 实时消息传递，流式输出 KP 思考过程
- **投骰系统** - 快捷投骰（d4-d100），全屏大字体动画，成功/失败判定
- **存档系统** - 保存/加载游戏进度
- **暗幕主题** - OKLCH 色彩空间暗黑/亮色双主题，Grimoire 风格侧边栏
- **角色卡** - 属性面板（力量/敏捷/体质/智力/感知/魅力），生命/护甲战斗数据，特质标签
- **角色状态追踪** - AI KP 自动追踪角色状态变化（HP 增减、属性变化），实时更新角色面板
- **行动建议** - 上下文推导的行动建议 Chips，点击快速输入
- **流式输出** - KP 回复末尾流式光标动画，思考内容直接显示在消息流中

## 技术栈

### Backend
- **FastAPI** - Python Web 框架
- **SQLAlchemy** - ORM
- **MySQL** - 数据库
- **WebSocket** - 实时通信
- **AI Gateway** - 支持多种 AI 提供商

### Frontend
- **React 19** + TypeScript
- **Vite** - 构建工具
- **Ant Design** - UI 组件库
- **Zustand** - 状态管理
- **React Router** - 路由

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- MySQL 5.7+

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd helloGolang
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 复制环境变量配置
cp ../.env.example .env
# 编辑 .env，填入你的数据库和 JWT 配置
```

### 3. 配置前端

```bash
cd frontend

# 安装依赖
npm install
```

### 4. 启动服务

```bash
# 启动后端（后端目录）
cd backend
uvicorn main:app --reload

# 启动前端（新终端窗口）
cd frontend
npm run dev
```

### 5. 访问

- 前端: http://localhost:5173
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## 使用说明

### 首次使用

1. 注册账号并登录
2. 在「AI 配置」页面添加你的 AI API 密钥（支持 DeepSeek/Claude/MiniMax）
3. 创建战役 — 可选择预设剧本（D&D/CoC/修仙）或自定义剧本
4. 进入战役房间，预设剧本会自动显示开场白和行动建议
5. 开始跑团！

### 预设剧本

| 剧本 | 系统 | 风格 |
|------|------|------|
| ⚔ 遗忘国度的阴影 | D&D 5e | 奇幻冒险 |
| ✦ 阿卡姆谜案 | CoC 7th | 恐怖推理 |
| ☵ 青云问道 | 修仙 | 东方玄幻 |

### 聊天操作

- 直接输入文字与 KP 对话
- 点击行动建议 Chips 快速输入
- 点击快捷投骰按钮（侧边栏）进行投骰
- Enter 发送，Shift+Enter 换行

## 项目结构

```
helloGolang/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── routers/             # API 路由
│   ├── schemas/             # Pydantic 模型
│   ├── services/            # 业务逻辑
│   │   ├── ai_gateway.py    # AI 网关
│   │   ├── chat_session.py  # 聊天会话
│   │   └── dice.py          # 投骰逻辑
│   └── utils/               # 工具函数
├── frontend/
│   └── src/
│       ├── pages/           # 页面组件
│       │   ├── Dashboard.tsx    # 大厅（战役/角色/AI管理）
│       │   ├── ChatRoom.tsx     # 游戏房间
│       │   ├── Login.tsx        # 登录
│       │   └── Register.tsx     # 注册
│       ├── services/        # API 服务
│       ├── stores/          # 状态管理（Zustand）
│       ├── hooks/           # 自定义 Hook（useTheme）
│       ├── data/            # 预设数据（presets）
│       └── styles/          # 主题样式
├── TODO.md                  # 开发待办清单
└── CHANGES.md               # 修改记录（本地，不提交）
```

## API 文档

详细 API 文档请访问 http://localhost:8000/docs（启动后端后）。

主要端点：

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录 |
| GET | /api/campaigns | 获取战役列表 |
| POST | /api/campaigns | 创建战役 |
| GET | /api/ai-configs | 获取 AI 配置 |
| POST | /api/ai-configs | 创建 AI 配置 |
| PUT | /api/ai-configs/{id} | 更新 AI 配置 |
| DELETE | /api/ai-configs/{id} | 删除 AI 配置 |
| POST | /api/ai-configs/{id}/activate | 激活 AI 配置 |
| GET | /api/characters | 获取角色卡列表 |
| POST | /api/characters | 创建角色卡 |
| WS | /ws/{campaign_id} | WebSocket 聊天 |

## License

MIT
