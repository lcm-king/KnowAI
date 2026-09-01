# 知学AI（KnowAI）· AI 个性化学习平台

> 独立全栈开发 · 让每个学习者拥有专属 AI 学伴
>
> **AI 多智能体（LangChain + LangGraph）+ 电商级高并发秒杀**双主线架构，覆盖"选课 → 学习 → 出题 → 批改 → 答疑"完整学习闭环。

## ✨ 项目亮点

- **多 Agent AI 能力**：基于 LangChain + LangGraph 搭建四个独立 AI 工作流（课程推荐 / 智能出题 / 作业批改 / 知识库对话），共用 ChromaDB 课程知识库做 RAG
- **高并发秒杀**：Redis 预减库存 + 令牌桶限流 + RabbitMQ 异步下单（5 个 Worker），单机支撑 2000+ QPS
- **数据一致性**：预减库存 + 异步下单 + 失败回补 + 30s 过期订单扫描，保证库存最终一致
- **多数据源架构**：MySQL（主数据）/ MongoDB（学习行为）/ Elasticsearch（课程检索，IK 分词）/ ChromaDB（知识向量），各司其职
- **全容器化部署**：Docker Compose 一键编排 8 个服务

## AI 能力（多 Agent 工作流）

| AI 能力 | 接口 | 说明 |
|---------|------|------|
| 课程推荐 | `POST /ai/knowledge/recommend` | 用户学习需求 → 意图理解 + 知识库 RAG → 匹配课程 |
| 智能出题 | `POST /ai/knowledge/quiz` | 课程知识库检索知识点 → LLM 生成测验题（含解析）|
| 作业批改 | `POST /ai/knowledge/grade` | 学生作答 + 参考答案 → LLM 评估打分 + 评语 |
| 知识库对话 | `POST /ai/knowledge/chat` | 课件向量检索 → 拼上下文 → LLM 流式回答，支持多会话历史 |
| 课件索引 | `POST /ai/knowledge/refresh/{course_id}` | 讲师上传新课件后重建该课程向量索引 |

技术细节：自定义 `HttpEmbeddings`（OpenAI 兼容 embedding，绕开 tiktoken 依赖）接入 ChromaDB；对话模型 `ChatOpenAI` 统一封装，可切换各家模型。

## 高并发秒杀架构

```
库存预热 Redis → 令牌桶限流 → Redis 原子扣减（DECR/Lua 防超卖）
→ RabbitMQ 异步下单（5 Worker）→ MySQL 订单落库
→ 分布式锁 + 唯一订单号防重复 → 失败回补库存
```

后台任务（FastAPI lifespan 启动）：秒杀消费 Worker、30s 过期订单扫描、30s 过期秒杀关闭、ES 课程索引同步。

## 业务模块

- **学生端**：课程浏览/搜索、购物车、秒杀下单、在线支付、学习进度、笔记、收藏、评价、AI 学伴对话/出题/批改
- **讲师端**：课程与课件管理、AI 知识库刷新、数据看板（ECharts）
- **管理端**：课程/用户/订单/秒杀活动管理

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Element Plus + Vant + ECharts |
| 后端 | FastAPI + SQLAlchemy 2.0 (async) + Pydantic v2 |
| AI | LangChain + LangGraph + ChromaDB + 自定义 HttpEmbeddings |
| 数据 | MySQL 8 / Redis 7 / MongoDB 6 / Elasticsearch 8 (IK) |
| 异步 | RabbitMQ（秒杀下单队列）|
| 认证 | JWT + Redis Token 状态 |
| 部署 | Docker Compose + Nginx 反代 |

## 数据架构

| 存储 | 职责 |
|------|------|
| MySQL | 用户 / 课程 / 订单 / 秒杀记录（事务主数据）|
| Redis | 缓存 / 秒杀预减库存 / Token / 限流 |
| MongoDB | 学习进度 / 笔记 / 聊天记录（行为数据）|
| Elasticsearch | 课程全文检索（IK 中文分词）|
| ChromaDB | AI 课程知识库向量 |

## 快速开始

```bash
# 方式一：Docker Compose 一键启动
cp .env.docker .env
bash start.sh

# 方式二：前后端分别启动（本地开发）
cd knowai_backend && pip install -r requirements.txt && uvicorn app.main:app --port 8000
cd knowai_frontend && npm install && npm run dev
```

- 前端：`http://localhost`
- 后端接口：`http://127.0.0.1:8000`
- Swagger 文档：`http://127.0.0.1:8000/docs`

## 目录结构

```text
知学AI/
├── knowai_backend/
│   ├── app/
│   │   ├── routers/      # auth/admin/ai_new/courses/orders/seckill/pay/search...
│   │   ├── services/     # LangChain 工作流、知识库、embedding
│   │   ├── tasks/        # 秒杀消费 Worker、过期订单/秒杀扫描
│   │   ├── crud/         # 数据访问层
│   │   ├── models.py     # SQLAlchemy ORM
│   │   └── main.py       # FastAPI 入口（lifespan 启动后台任务）
│   └── docker-compose.yml
├── knowai_frontend/      # Vue3 + TS + ElementPlus + Vant
└── docs/                 # 技术实现详解、业务分析文档
```

## 部署说明

详见 `DOCKER_README.md`：生产镜像（gunicorn + uvicorn workers）、前端多阶段构建、Nginx 静态托管与 `/api` 反代。
