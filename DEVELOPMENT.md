# Think Land 开发文档

> 本文档采用增量更新模式，每次代码变更后同步记录。
> 最后更新：2026-05-19

---

## 一、项目概述

Think Land 是一个面向个人创作者的产品灵感梳理与规划工具，通过 AI 辅助将用户的一句话产品想法转化为结构化的 PRD、流程图和任务计划，并支持社区内容发布与互动。

### 核心功能

| 功能 | 说明 |
|------|------|
| 用户注册 / 登录 | JWT Token 认证 |
| AI 配置 | 用户自行配置 Base URL / Model / API Key |
| 创意对话 | 多轮对话持久化，AI 持续追问并生成结构化内容 |
| PRD 生成 | 根据对话生成产品需求文档 |
| 流程图 | 将 PRD 转化为可视化的业务流程节点 |
| 任务计划 | 从 PRD 和流程图中拆解可执行任务 |
| 创意社区 | 发布 / 浏览 / Star 公开 PRD 或上线项目 |

---

## 二、技术栈

### 前端
- **框架**：Vue 3 (Composition API) + Vue Router
- **构建**：Vite
- **样式**：原生 CSS（CSS 变量 + BEM 命名）
- **字体**：Fraunces (Display) + Figtree (Body) + JetBrains Mono (Mono)

### 后端
- **框架**：FastAPI (Python)
- **数据库**：MySQL 8 + SQLAlchemy 2 (ORM)
- **认证**：JWT (python-jose)
- **AI 接入**：用户自配置 API（支持 OpenAI 兼容接口）

---

## 三、数据库模型

### users
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| account | VARCHAR(191) | 登录账号（唯一） |
| password_hash | VARCHAR(191) | bcrypt 哈希 |
| role | VARCHAR(32) | normal / admin |
| granted_points | INT | 每日赠送点数 |
| used_points | INT | 当日已用点数 |
| last_point_reset | DATETIME | 上次点数重置时间 |
| created_at | DATETIME | 创建时间 |

### user_ai_configs
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| user_id | BIGINT | 外键 → users |
| base_url | VARCHAR(512) | API 端点 |
| model | VARCHAR(128) | 模型名称 |
| api_key_encrypted | TEXT | 加密存储的 API Key |

### conversations
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| user_id | BIGINT | 外键 → users |
| title | VARCHAR(191) | 对话标题（取首条用户消息） |
| status | VARCHAR(32) | draft / confirmed |
| result_json | JSON | 包含 messages/prd/flow/tasks |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

### conversation_messages
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| conversation_id | BIGINT | 外键 → conversations |
| user_id | BIGINT | 外键 → users |
| role | VARCHAR(32) | user / assistant |
| content | TEXT | 消息内容 |
| sequence_index | INT | 顺序索引（唯一约束） |

### community_items
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| owner_user_id | BIGINT | 外键 → users |
| source_conversation_id | BIGINT | 来源对话（可为 null） |
| item_type | VARCHAR(32) | prd / project |
| title | VARCHAR(191) | 标题 |
| summary | TEXT | 简介 |
| content_json | JSON | 包含 prd / flow / tasks |
| project_url | VARCHAR(512) | 项目链接（project 类型） |
| status | VARCHAR(32) | published（默认） |
| star_count | INT | 被 Star 次数 |
| created_at | DATETIME | 发布时间 |
| updated_at | DATETIME | 更新时间 |

### community_stars
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| item_id | BIGINT | 外键 → community_items |
| user_id | BIGINT | 外键 → users |
| created_at | DATETIME | Star 时间 |

### generation_records
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| user_id | BIGINT | 外键 → users |
| prompt | TEXT | 用户输入文本 |
| result_json | JSON | AI 返回的完整结果 |
| model | VARCHAR(128) | 使用的模型 |
| prompt_tokens | INT | 提示 token 数 |
| completion_tokens | INT | 完成 token 数 |
| total_tokens | INT | 总 token 数 |
| points_used | INT | 本次消耗点数 |
| created_at | DATETIME | 创建时间 |

### point_transactions
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 主键 |
| user_id | BIGINT | 外键 → users |
| generation_id | BIGINT | 外键 → generation_records（可 null） |
| delta | INT | 点数变化（正数为获得，负数为消耗） |
| token_count | INT | 消耗 token 数 |
| reason | VARCHAR(64) | 原因描述 |
| created_at | DATETIME | 交易时间 |

---

## 四、API 接口

### 认证
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/auth/register | 注册 |
| POST | /api/auth/login | 登录，返回 JWT |
| GET | /api/me | 获取当前用户信息 + 点数 + AI 配置 |

### AI 生成
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/generate | 发送对话消息，返回 AI 回复（支持多轮 conversation_id） |
| POST | /api/conversations/confirm | 确认并保存当前对话需求 |

### 创意社区
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/community/items | 获取社区内容列表（支持 item_type 筛选） |
| POST | /api/community/items | 发布内容（PRD 或项目） |
| POST | /api/community/items/{item_id}/star | Star 或取消 Star |

---

## 五、前端页面

### HomeView (`/`)
- 品牌首页，展示产品理念
- Hero 区域：标题 + 动画窗口（PRD 卡片 + 流程图动画）
- 功能介绍三栏
- 动态演示区

### AuthView (`/login`)
- 登录 / 注册切换 Tab
- 左侧品牌文案 + 右侧表单卡片
- 三栏展示用户类型

### WorkspaceView (`/workspace`)
- **侧边栏**：Logo + 导航（工作台 / PRD / 流程图 / 任务 / 社区）+ 用户信息
- **聊天视图**：消息列表 + 记忆时间线 + 输入框
- **PRD 视图**：生成的需求文档列表
- **流程图视图**：节点 + 连接线可视化
- **任务视图**：四栏任务卡片
- **社区视图**：发布表单 + 内容卡片网格

---

## 六、版本日志

### v0.0.4 (2026-05-19) — 生成动画演示弹窗
**新增「生成动画」全流程演示卡片**
- 弹窗形式展示完整 AI 生成 → 代码 → 部署 → 上线预览流程
- **四阶段步骤导航**：自然语言输入 → 生成代码 → 部署上线 → 查看站点
- Phase 0（自然语言）：终端打字机效果 + PRD 预览卡片
- Phase 1（生成代码）：深色代码编辑器，逐行高亮语法关键词 (keyword/string/comment/func/var)
- Phase 2（部署中）：火箭轨道旋转动画 + 进度条 + 部署日志逐步显示
- Phase 3（上线预览）：完整浏览器外壳 + 模拟产品页面（导航/英雄区/功能卡片）
- 支持上一步/下一步手动切换，自动阶段触发动画
- 底部 CTA：前3步显示「下一步→」，最后一步跳转登录页「开始使用→」

### v0.0.3 (2026-05-19) — Editorial Studio UI 升级
**设计语言全面重构**
- 字体：Fraunces serif（展示标题）+ Figtree（正文）+ JetBrains Mono（代码/标签）
- 配色：Ink Black `#171426` + Parchment Cream `#fdfaf5` + Terracotta `#c4622d` + Forest Green `#2d6a4f`
- 背景：暖米色径向渐变 + 低饱和度色块，营造纸质感编辑室氛围
- 卡片：半透明毛玻璃效果 + 柔和暖色阴影
- 动效：页面渐入、卡片悬浮浮动、记忆轨道 hover 展开、流畅的 cubic-bezier 过渡
- 侧边栏用户信息独立区块，settings 按钮 hover 旋转变作
- 社区卡片：进入动画（countUp）+ hover 上浮 + 边框高亮
- Home 页面：Hero 节点色相更新（赭石/森林绿/天空蓝），流程线颜色呼应主题
- Auth 页面：展示区三栏配色改为深色系渐变（Ink + Terra + Sky）
- index.html 引入 Google Fonts CDN 完整字体包

### v0.0.2 (2026-05-19)
**功能新增**
- 新增 `Conversation` / `ConversationMessage` 模型 — 支持多轮对话持久化
- 新增 `CommunityItem` / `CommunityStar` 模型 — 社区内容发布与 Star 机制
- 新增 `PointTransaction` 点数消费记录表
- 后端新增 `/api/community/*` 系列 API

**前端升级（UI/UX 大改版）**
- 采用 Editorial Studio 美学：Fraunces serif 展示字体 + Figtree 几何无衬线正文字体
- 配色体系改为暖色调：Ink Black + Parchment 米白背景 + Terracotta 赭色强调 + Forest Green 成功状态
- 记忆时间线交互升级：hover 展开显示完整内容预览
- 社区页面新增发布面板、Star 按钮、内容卡片网格
- 侧边栏用户信息区块独立显示

**其他**
- 新增 `.gitignore`、`.env.example`
- 错误信息中→英国际化
- 新增迁移 SQL 脚本

### v0.0.1 (2026-05-19)
- 初始代码提交：注册/登录/AI配置/对话生成PRD/流程图/任务计划基础功能