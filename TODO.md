# Tabletop Agent - 开发待办清单

## 当前已实现功能

- ✅ 用户注册/登录
- ✅ 战役管理（创建、编辑、删除）
- ✅ AI KP 配置（DeepSeek/Claude/MiniMax）
- ✅ 实时聊天（WebSocket）
- ✅ AI 流式输出（KP思考过程）
- ✅ 投骰系统
- ✅ 存档系统

---

## 待开发功能

### P0 - 核心体验（必须解决）

- [ ] **记忆持久化**
  - 问题：每次进入战役聊天，之前的记录会清空
  - 原因：会话状态存储在内存中，刷新/重连后丢失
  - 方案：使用 Redis 存储会话状态
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/1

### P1 - 用户体验优化

- [ ] **思考窗口折叠/展开**
  - KP思考过程显示在可折叠区域
  - 用户可选择展开查看或收起
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/2

- [ ] **角色卡预设模板**
  - 添加多个预设人设（如：战士、法师、盗贼、猎人等）
  - 随机生成角色（种族+年龄+职业+背景）
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/3

- [ ] **人设扩展**
  - 添加性格特征（MBTI/大五人格简化版）
  - 添加SAN值（理智值）状态
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/4

### P2 - 多人游戏

- [ ] **AI队友模式**
  - 支持用户+AI队友双人跑团
  - AI队友根据角色卡性格自主行动
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/5

### P3 - 智能增强

- [ ] **用户画像分析**
  - 抽取用户行为逻辑
  - 分析玩家性格特征（激进/保守/探索型等）
  - KP根据用户性格调整剧情难度和风格
  - 关联issue: https://github.com/Inorysekiro2333/Tabletop-Agent/issues/6

---

## 技术债务

- [ ] 添加单元测试
- [ ] API限流保护
- [ ] WebSocket重连优化
- [ ] 数据库索引优化

---

## 可能的技能增强

| 任务 | 推荐Skill | 安装量 | 安装命令 |
|------|-----------|--------|----------|
| Redis集成 | `redis/agent-skills@redis-development` | 1.2K | `npx skills add redis/agent-skills@redis-development -g -y` |
| 后端测试 | `supercent-io/skills-template@backend-testing` | 11.8K | `npx skills add supercent-io/skills-template@backend-testing -g -y` |
| 测试策略 | `supercent-io/skills-template@testing-strategies` | 11.2K | `npx skills add supercent-io/skills-template@testing-strategies -g -y` |
| WebApp测试 | `anthropics/skills@webapp-testing` | 35.8K | `npx skills add anthropics/skills@webapp-testing -g -y` |
| CI/CD | `mindrally/skills@ci-cd-best-practices` | 395 | `npx skills add mindrally/skills@ci-cd-best-practices -g -y` |

更多skills: https://skills.sh/

---

## 优先级建议

| 优先级 | 功能 | 理由 |
|--------|------|------|
| P0 | 记忆持久化 | 核心体验，数据丢失问题 |
| P1 | 思考窗口折叠 | 用户反馈强烈 |
| P1 | 角色卡模板 | 降低新手门槛 |
| P2 | AI队友 | 差异化竞争点 |
| P3 | 用户画像 | 长期智能化的基础 |
