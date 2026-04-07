# Tabletop Agent

TRPG（桌面角色扮演游戏）AI KP（主持人）助手，基于 Web 的实时跑团平台。

## 功能

- **用户系统** - 注册、登录、角色管理
- **战役管理** - 创建、编辑、删除跑团战役
- **AI KP** - 支持 DeepSeek/Claude/MiniMax 等大模型作为 KP
- **实时聊天** - WebSocket 实时消息传递，流式输出 KP 思考过程
- **投骰系统** - 内置 D&D 风格投骰，支持快捷投骰
- **存档系统** - 保存/加载游戏进度

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
3. 创建战役并选择 AI 配置
4. 进入战役房间，开始跑团

### 聊天命令

- 直接输入文字与 KP 对话
- 输入 `/roll 1d20+5` 进行投骰
- 点击快捷按钮进行快速投骰

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
│       ├── services/        # API 服务
│       └── stores/          # 状态管理
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

## License

MIT
