# Personal Agent Team 🤖

多智能体协作系统 - 你的个人 AI 助理平台

## 项目结构

```
agent_team/
├── frontend/              # Next.js 15 前端
│   ├── src/
│   │   ├── app/           # 页面路由
│   │   ├── components/    # React 组件
│   │   ├── lib/           # API 客户端
│   │   └── stores/        # Zustand 状态管理
│   └── Dockerfile
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── agents/        # Agent 实现
│   │   │   ├── chief/     # 调度中心
│   │   │   ├── career/    # 职业发展
│   │   │   ├── research/  # 学术研究
│   │   │   ├── life/      # 生活管理
│   │   │   ├── study/     # 学习规划
│   │   │   ├── finance/   # 财务管理
│   │   │   ├── travel/    # 旅行规划
│   │   │   └── health/    # 健康管理
│   │   ├── tools/         # 统一工具层
│   │   ├── core/          # 核心逻辑
│   │   ├── api/           # API 路由
│   │   ├── models/        # 数据模型
│   │   └── schemas/       # Pydantic Schemas
│   ├── tests/             # 测试
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── docs/
```

## 快速开始

### 1. 环境配置

```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 2. 后端启动（需要本地 MongoDB）

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端: http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat` | 主聊天入口 |
| GET  | `/api/v1/tasks` | 获取任务列表 |
| GET  | `/api/v1/tasks/{id}` | 获取任务详情 |
| POST | `/api/v1/tasks/{id}/retry` | 重试失败任务 |
| GET  | `/health` | 健康检查 |

## Agent 说明

### 核心 Agent (P0 - MVP)

- **Chief Agent** - 任务调度中心，理解意图、拆解任务、分发给专业 Agent
- **Career Agent** - 职业发展助手：JD分析、简历优化、面试准备
- **Research Agent** - 学术研究助手：论文摘要、科研日报、文献综述
- **Life Agent** - 生活管理助手：Todo管理、文件整理、日程规划

### 扩展 Agent

- **Study Agent** (P1) - 学习规划助手：目标拆解、路径规划、资源推荐、进度跟踪
- **Finance Agent** (P2) - 财务管理助手：消费记录、支出分析、预算管理、订阅管理
- **Travel Agent** (P2) - 旅行规划助手：行程规划、住宿推荐、交通方案、预算估算
- **Health Agent** (P3) - 健康管理助手：健康记录、趋势分析、目标追踪、健康报告

## 测试

```bash
cd backend
pytest tests/ -v
```

## 技术栈

- **前端**: Next.js 15 + TypeScript + Tailwind CSS + Zustand
- **后端**: FastAPI + Motor (MongoDB) + Celery
- **Agent**: Qwen API (DashScope OpenAI 兼容模式)
- **部署**: 直接运行（无 Docker 依赖）
