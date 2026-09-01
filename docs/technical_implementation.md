知学AI — 技术实现详解文档

一、项目技术栈总览

架构层：前端层(Vue 3 + TypeScript)，Vue Router + Pinia + ElementPlus + Vant + Axios + ECharts，HTTP/WebSocket 连接 API 网关(Nginx)，反向代理 /api/ 到 backend:8000，后端层(FastAPI + Python 3.11)，分为认证系统(JWT+Redis, bcrypt)、业务模块(课程/订单/秒杀/支付)、AI 服务(LangChain, ChromaDB)、后台任务系统(秒杀/订单/ES同步)，数据存储层包括 MySQL(核心业务数据)、Redis(缓存/秒杀/Token)、MongoDB(用户行为数据)、Elasticsearch(课程全文搜索，IK分词)、ChromaDB(AI 知识库向量存储)。

技术选型表：

前端框架：Vue 3 (Composition API + script setup)，版本 3.x，用途：前端核心框架
构建工具：Vite，版本 5.x，用途：前端构建与 HMR
类型系统：TypeScript，版本 5.x，用途：类型安全
状态管理：Pinia，版本 2.x，用途：全局状态
UI 组件：Element Plus / Vant，版本最新，用途：PC + 移动端组件
HTTP 客户端：Axios，版本 1.x，用途：API 请求
路由：Vue Router，版本 4.x，用途：前端路由
图表：ECharts，版本 5.x，用途：讲师/管理员数据看板
后端框架：FastAPI，版本 0.109+，用途：异步 Python Web 框架
ORM：SQLAlchemy (async)，版本 2.x，用途：MySQL 异步 ORM
认证：python-jose + passlib(bcrypt)，版本最新，用途：JWT + 密码哈希
数据库：MySQL 8.0，版本 8.0，用途：核心业务数据
缓存：Redis 7，版本 7-alpine，用途：缓存/秒杀/Token
行为数据：MongoDB 6，版本 6，用途：进度/笔记/聊天
搜索：Elasticsearch 8.10 + IK，版本 8.10.2，用途：课程全文搜索
消息队列：RabbitMQ，版本 3-management，用途：预留消息队列
AI 框架：LangChain + LangGraph，版本最新，用途：AI 工作流编排
向量库：ChromaDB，版本最新，用途：知识库向量存储
部署：Docker Compose，版本最新，用途：容器编排


二、后端架构详解

2.1 应用启动流程

源码位置：knowai_backend/app/main.py

使用 FastAPI 的 lifespan 协议（替代旧的 startup/shutdown 事件）管理应用生命周期：

startup 阶段：初始化数据库连接，包括 init_db() 创建 MySQL 表、init_mongo() 连接 MongoDB 并创建索引、init_redis() 连接 Redis、init_es_index() 初始化 Elasticsearch 索引。然后启动后台任务：consume_seckill_queue (5 个秒杀 Worker)、check_expired_orders (每 30s 取消过期订单)、check_expired_seckills (每 30s 关闭过期秒杀)、sync_courses_to_es (ES 同步)。

shutdown 阶段：通过 asyncio.Event() 控制优雅关闭，await asyncio.gather 等待所有任务完成。

实现要点：后台任务通过 asyncio.Event() 控制优雅关闭，所有数据库连接在启动时一次性初始化。

2.2 数据库连接层

源码位置：knowai_backend/app/database.py

SQLAlchemy 异步引擎：create_async_engine(settings.mysql_url, pool_size=20, max_overflow=10)，使用 async_sessionmaker(engine, expire_on_commit=False) 创建会话工厂。

Redis 客户端：全局单例 redis_client，通过 Redis.from_url(settings.redis_url, decode_responses=True) 初始化。注意 decode_responses=True 使返回的字符串自动解码为 Python 字符串而非字节。

MongoDB 客户端：使用 Motor (AsyncIOMotorClient) 异步 MongoDB 驱动，连接 settings.mongodb_url，启动时创建索引：users(phone)、chat_messages(user_id+session_id)、lesson_progress、course_progress、lesson_notes。

数据库选型理由：
MySQL 8.0：核心业务需要 ACID 事务保证（订单、秒杀）
Redis 7：高并发场景，原子操作（DECR 扣库存、令牌桶限流）
MongoDB 6：用户行为数据结构灵活（进度 JSON、笔记、聊天记录），无需预定义 Schema
Elasticsearch 8.10：全文搜索需求，IK 中文分词

2.3 配置管理

源码位置：knowai_backend/app/config.py

使用 Pydantic BaseSettings 从环境变量加载配置。核心字段包括：应用(app_env, debug)、MySQL(mysql_host/port/user/password/database)、Redis/MongoDB/ES(redis_url, mongodb_url, elasticsearch_host)、AI(openai_api_key, openai_base_url, llm_model, embedding_api_key/base_url/model)、JWT(jwt_secret_key, jwt_algorithm, access_token_expire_minutes)、支付(pay_mock, alipay_sandbox)、SMS(sms_mock, cloopen_account_sid)。提供计算属性 mysql_url 和 cors_origin_list。

通过 @lru_cache() 实现单例模式。

设计要点：全部配置通过环境变量注入，使用 Pydantic BaseSettings 自动类型转换；@lru_cache 实现单例模式，性能优化；敏感信息（密码、密钥）不硬编码，通过环境变量或 .env 文件传入。


三、认证系统 (JWT + Redis)

3.1 认证流程

登录流程：用户密码 -> bcrypt 验证 -> 生成 JWT -> payload 中包含 sub=user_id, jti=uuid4, role, iat, exp -> Redis 记录 token:{user_id}:{jti} = "1"

请求验证流程：请求到达 -> 从 Authorization Header 提取 Bearer token -> JWT 解码验证签名 -> 提取 user_id + jti -> Redis 查询 token 是否有效 -> 有效则返回当前用户，无效则 401 未认证

登出/踢下线流程：调用 /logout -> Redis 删除 token 记录；管理员封禁 -> Redis 设置封禁标记

3.2 Token 创建源码分析

源码位置：knowai_backend/app/auth.py

create_user_access_token 函数：获取当前时间 (datetime.now(timezone.utc))，生成唯一令牌 ID (str(uuid4()))，构建 payload 包含 sub (用户ID)、jti (令牌唯一标识)、role (角色: student/teacher/admin)、iat (签发时间)、exp (过期时间，默认 7 天)。使用 jwt.encode(payload, secret_key, algorithm) 编码。将 jti 存入 Redis，设置过期时间与 token 一致。返回 token 字符串。

3.3 用户身份依赖注入

get_current_user 依赖项：从 OAuth2 密码流的 Header 提取 Bearer token -> 解码 JWT 提取 user_id 和 jti -> 检查 Redis 中 token 是否有效（未登出）-> 从数据库加载用户 -> 检查用户是否 active -> 返回用户或 401

get_current_user_optional 依赖项：尝试调用 get_current_user，捕获 HTTPException 返回 None，不抛出异常。用于支持游客访问课程详情页和搜索。

角色守卫：get_current_teacher 检查 role == teacher，get_current_admin 检查 role == admin，通过 Depends 链式注入。

设计亮点：get_current_user_optional 支持游客访问课程详情页和搜索；JWT 不存储状态，状态管理在 Redis（支持登出和封禁）；使用 jti（UUID）防止 Token 重放攻击；3 层角色守卫：user -> teacher -> admin。


四、秒杀系统（核心技术亮点）

4.1 系统架构

秒杀系统分为三个阶段：

准备阶段：管理员创建活动 -> 预热: Redis 写入库存 seckill:stock:ID = 库存量

请求阶段：用户请求 -> 令牌桶全局限流 100rps -> 用户级限流 1次/秒/人 -> Redis DECR 库存 -> 判断库存>0 -> 推送到队列 -> 返回排队ID

异步处理阶段：Worker 从队列获取任务 -> MySQL 行锁 SELECT...FOR UPDATE -> 检查活动/库存/重复购买 -> 通过则创建订单+条目，失败则恢复 Redis 库存 -> 写入秒杀结果

4.2 三层限流实现

第一层：令牌桶算法（全局限流），使用 Lua 脚本保证原子性。源码位置：knowai_backend/app/utils/rate_limiter.py。Lua 脚本逻辑：读取 key 的 tokens 和 updated_at，如果不存在则初始化为容量。基于时间差补充令牌（delta * refill_rate），不超过容量。判断 tokens 是否大于等于 requested，是则扣减并返回 1，否则返回 0。key 设置 120s 过期。

第二层：用户级别 1rps，使用 Redis SET NX EX 1 命令，key 为 rate:seckill:{user_id}:{activity_id}，如果 key 已存在则拒绝，确保同一用户每秒只能请求一次。

第三层：Redis DECR 原子扣库存，源码在 routers/seckill.py。remaining = redis.decr(stock_key) 原子减1，如果 remaining < 0 则 redis.incr(stock_key) 恢复并返回已售罄，否则推送到队列。

4.3 异步消费者（5 Workers）

源码位置：knowai_backend/app/tasks/seckill_consumer.py

_seckill_worker 函数：传入 stop_event 和 worker_id，循环监听队列。使用 redis.blmove 命令原子地从 LEFT 弹出一个元素并推向 RIGHT (处理中列表)，block 时间 5 秒。获取到任务后在 MySQL 事务中处理：with_for_update() 行锁查询活动，检查活动有效（状态/时间）、SKU 可用、课程已发布、重复购买检查、SKU 库存扣减、活动库存扣减、创建订单和 OrderItem。如果秒杀价为 0 则直接开通课程权限。成功后将结果通过 redis.setex 写入 Redis，前端轮询获取。

若失败（ValueError 或 HTTPException），通过 redis.incr 恢复 Redis 库存（因为 DECR 已应用），写入失败结果。

4.4 崩溃恢复机制

_recovery_worker 函数：每 60 秒执行一次。扫描所有 Worker 的处理中列表 (processing:{worker_id})，对每个条目检查锁 (seckill:lock:{queue_id}) 是否存在。如果锁不存在（说明 Worker 已崩溃，锁已过期），则将该条目重新入队到主队列。

4.5 整体时序

用户点击秒杀 -> 前端 POST /seckill/{id} -> FastAPI 接口 -> 令牌桶 Lua + 用户限流 -> 通过 -> Redis DECR 库存 -> 剩余>0 -> RPUSH 队列 -> 返回排队ID -> 前端开始轮询 /seckill/result

Worker 通过 BLMOVE 从队列弹出 -> SELECT...FOR UPDATE 行锁 -> 创建订单+OrderItem -> 成功 -> Redis SETEX 结果 -> 前端获取结果 -> 跳转支付页


五、支付系统

5.1 支付宝集成

源码位置：knowai_backend/app/services/alipay.py

使用 alipay SDK 创建 AliPay 客户端。new AliPay(appid, app_notify_url, app_private_key_string, alipay_public_key_string, sign_type="RSA2", debug=settings.alipay_sandbox)。debug=True 为沙箱模式。

create_alipay_order 函数：调用 alipay.api_alipay_trade_page_pay(out_trade_no=订单号, total_amount=金额, subject=商品描述, return_url=同步跳转, notify_url=异步通知) 获取支付宝支付链接。返回拼接的支付宝网关 URL。

注意私钥格式支持 PKCS1 和 PKCS8，通过自动检测处理。

5.2 支付状态轮询

源码位置：knowai_backend/app/routers/pay.py

POST /pay/create 接口：获取订单，检查支付模式。如果 pay_mock=True，则通过 background_tasks.add_task(simulate_pay_success, order_sn) 触发模拟支付，5 秒后后台自动确认。如果真实支付宝支付，则调用 create_alipay_order 返回支付 URL。

simulate_pay_success 函数：await asyncio.sleep(5) 模拟 5 秒支付处理，然后调用 mark_order_paid 更新订单状态并开通课程权限。

mark_order_paid 函数：SQLAlchemy 事务内 with_for_update() 行锁查询订单 -> 更新 status=paid 和 pay_time -> 调用 grant_courses_for_order 创建 UserCourse 记录开通课程 -> 删除购物车中相关商品。

前端轮询：用户扫码支付后，前端每隔 2 秒调用 GET /pay/status/{sn} 查询订单状态，直到订单已支付或超时取消。

5.3 支付通知（支付宝异步）

POST /pay/notify/alipay 接口：获取支付宝 POST 表单数据，调用 alipay.verify(form, form.get("sign")) 验证签名。签名验证通过后检查 trade_status == "TRADE_SUCCESS"，调用 mark_order_paid。返回 "success" 给支付宝（支付宝要求返回 success）。


六、AI 智能系统

6.1 整体架构

AI 模块分为四层：

顶层是 LangGraph 多智能体工作流，包含三个工作流：推荐工作流(parse -> RAG -> rank)、出题工作流(retrieve -> generate)、批改工作流(retrieve -> grade -> feedback)。

中间层是 ChromaDB 向量存储，负责知识库文档的分块、Embedding 计算和向量检索。

LLM 层使用兼容 OpenAI SDK 的 API，支持 SiliconFlow、OpenAI 或任意 OpenAI 兼容 API。

最底层是联网搜索 (DuckDuckGo) 用于补充实时信息。

6.2 知识库管理（ChromaDB + 自定义 Embedding）

源码位置：knowai_backend/app/services/knowledge_base.py

KnowledgeBaseManager 类：构造函数接收持久化目录，初始化 chromadb.PersistentClient。

_get_embedding 方法：调用 OpenAI 兼容的 Embedding API (HTTP POST 到 {embedding_base_url}/embeddings，请求体包含 input 文本和 model 名称，Authorization header 携带 API key)，返回 embedding 向量。

add_document 方法：获取或创建 ChromaDB collection (collection_name, 使用 cosine 距离, hnsw 空间)，异步批量获取 embeddings，将 ids/embeddings/documents/metadatas 添加到 collection。

search_similar 方法：获取指定课程的 collection (course_{course_id})，计算查询文本的 embedding，调用 collection.query 进行余弦相似度搜索，返回 k 个最相似的 Document 对象。

设计亮点：使用兼容 OpenAI SDK 的 Embedding API（可插拔：OpenAI / SiliconFlow / 阿里云）；ChromaDB 持久化存储，重启不丢失；支持增量添加（使用 get_or_create_collection）；余弦相似度搜索。

6.3 LangGraph 多智能体工作流

源码位置：knowai_backend/app/services/langgraph_workflow.py

以推荐工作流为例：

定义 RecommendState (TypedDict)，包含 user_input, intents, kb_context, recommendations。

定义三个节点函数：
parse_intent 节点：使用 LLM 的 structured_output 功能，调用 SystemMessage + HumanMessage 分析用户的学习需求，提取类别、难度级别、学习目标，输出到 state.intents。
retrieve_knowledge 节点：调用 kb_manager.search_all_courses 搜索知识库，将结果拼接到 state.kb_context。
rank_courses 节点：根据上下文和意图，调用 LLM 对候选课程排序，输出推荐列表。

构建 StateGraph：添加三个节点，设置边 parse -> retrieve -> rank -> END，设置入口点为 parse，编译为可执行图。

出题工作流和批改工作流类似，通过不同的节点组合实现不同功能。

6.4 AI 对话（带知识库 + 联网搜索）

POST /ai/knowledge/chat 接口的完整流程：

1. 搜索所有课程知识库：遍历所有已发布课程，调用 kb_manager.search_all_courses 检索相关文档，拼接为 kb_context。

2. 联网搜索：调用 search_web(message, max_results=5) 获取 DuckDuckGo 搜索结果，拼接为 web_text。

3. 从 MongoDB 加载聊天历史：查询 chat_messages 集合，按时间排序，取最近 20 条。如果有 session_id 参数则按会话加载。

4. 构建 System Prompt：设置系统角色为智能AI学习助手学伴，核心原则包括必须回答用户问题不能说不知道、优先基于知识库回答、结合搜索结果回答实时信息、使用自己的知识自信回答。提及课程名称时使用《》括起来。

5. 构建多轮对话消息：包含 SystemMessage、历史消息、参考信息（知识库+联网结果）、当前用户问题。

6. 调用 LLM：使用 ChatOpenAI(model, openai_api_key, openai_api_base) 异步调用。

7. 保存对话到 MongoDB：将用户消息和 AI 回复同时保存到 chat_messages 集合，更新 chat_sessions 的元数据。

8. 返回 ChatResponse(answer, mock=False)。如果 LLM 调用失败，返回 mock=True 的降级回复。


七、全文搜索（Elasticsearch + IK）

7.1 索引映射

源码位置：knowai_backend/app/utils/es.py

索引名称：courses

Settings：使用 ik_smart 分词器（IK 中文分词）。

Mappings 字段：title 类型 text，分析器 ik_max_word，权重 boost=3；description 类型 text，分析器 ik_smart，权重 boost=2；category 类型 keyword；teacher_name 类型 keyword；price 类型 float；learn_count 类型 integer；rating 类型 float；status 类型 keyword。

7.2 搜索查询

GET /search/courses 接口参数：q 搜索关键词、category 分类筛选、sort_by 排序字段、page/page_size 分页。

构建 ES 查询 body：bool 查询，must 部分使用 multi_match 多字段匹配 (title^3, description^2, category)，type=best_fields；filter 部分添加 status=published 过滤。如果指定了 category，追加 category 过滤。

Highlight：对 title 和 description 字段启用高亮，返回匹配片段。

排序：默认按 learn_count 降序，支持自定义 sort_by 字段。


八、ORM 模型设计（14张核心表）

表关系：users 一对多 orders、user_courses、favorites；users 一对一 teachers；teachers 一对多 courses；courses 一对多 course_skus、chapters、course_reviews、course_questions；course_skus 一对多 seckill_activities、order_items、user_courses；orders 一对多 order_items；chapters 一对多 lessons；lessons 一对多 lesson_knowledge；course_questions 一对多 course_answers。

关键模型定义（源码位置：knowai_backend/app/models.py）：

User 表：id、username(unique)、phone(unique)、email、password_hash、avatar、role(Enum: student/teacher/admin)、is_active(default=True)、teacher_id(FK teachers.id)、created_at。

Course 表：id、teacher_id(FK teachers.id)、title、description(Text)、cover、category、total_hours、learn_count(default=0)、rating(default=0.0)、status(Enum: draft/published/archived)。关系：teacher(back_populates courses)、skus(cascade delete)、chapters(order_by sort_order)。

Order 表：id、user_id(FK users.id)、order_sn(unique, indexed)、total_amount(Decimal(10,2))、pay_amount(Decimal(10,2))、status(Enum: pending/paid/cancelled等)、pay_time、expire_time、seckill_activity_id(FK seckill_activities.id)。关系：user、items(cascade delete)。


九、前端架构详解

9.1 路由守卫系统

源码位置：knowai_frontend/src/router/index.ts

路由定义：根路径 / 使用 MainLayout 组件嵌套子路由。公开路由包括 homepage(/)、courses(/courses)、course-detail(/course/:id)。需要认证的路由包括 cart、learn(/learn/:id)、teacher、admin。教师后台需要 teacher 或 admin 角色，管理员后台需要 admin 角色。独立路由 /login 用于登录页。其余路径匹配 404。

路由守卫 beforeEach 逻辑：检查用户 store 中是否有 token，如果没有则尝试从 localStorage 恢复会话 (tryRestoreSession)。如果需要认证但未登录，则跳转到登录页并附带 redirect 参数。如果路由指定了 roles 角色限制，检查当前用户角色是否在允许列表中，否则跳转首页。

9.2 前端状态管理 (Pinia)

源码位置：knowai_frontend/src/stores/user.ts

useUserStore 定义：state 包含 token（从 localStorage 读取）和 user（UserInfo | null）。getter 包括 isLoggedIn、isAdmin、isTeacher。

actions：
login：调用登录 API，保存 token 到 state 和 localStorage，调用 fetchMe 获取用户信息。
fetchMe：调用 GET /auth/me 接口，保存用户信息到 state。
tryRestoreSession：如果 localStorage 中有 token，尝试调用 fetchMe，失败则清除 token。
logout：清除 state 中的 token 和 user，删除 localStorage 中的 token。

9.3 HTTP 请求拦截器

源码位置：knowai_frontend/src/api/request.ts

创建 axios 实例，baseURL 从 VITE_API_BASE_URL 环境变量获取，默认为 /api，超时时间 30 秒。

请求拦截器：从 localStorage 获取 token，如果有则注入 Authorization: Bearer {token} header。

响应拦截器：正常响应返回 response.data（直接返回后端数据体）。错误时按状态码处理：401 清除登录状态并跳转登录页，403 显示无权限提示，429 显示请求频繁提示。其余错误返回 Promise.reject 由调用方处理。


十、订单创建（分布式锁 + 行级锁）

源码位置：knowai_backend/app/crud/order_crud.py

create_order 函数流程：

1. Redis 分布式锁：key 为 order:lock:{user_id}，使用 SET NX EX 5 设置，防止用户同时提交多个订单。如果获取锁失败则抛出 429。

2. MySQL 行锁查询 SKU：SELECT...FOR UPDATE 锁定 SKU 行，防止其他事务并发修改。

3. 检查库存：SKU 存在且 stock >= quantity，否则抛出 400 库存不足。

4. 扣减库存：sku.stock -= quantity。

5. 创建订单：生成 order_sn，设置 total_amount 和 pay_amount，expire_time 为当前时间 + 30 分钟。

6. 创建订单条目：OrderItem 关联 order_id 和 sku_id。

7. finally 块释放 Redis 分布式锁。


十一、Docker 部署架构

11.1 网关配置

Nginx 配置 (knowai_frontend/nginx.conf)：
监听 80 端口，根目录 /usr/share/nginx/html，默认文档 index.html，允许上传 200MB。
location /api/ 反向代理到 http://backend:8000/api/，设置 Host/X-Real-IP/X-Forwarded-For 等 header，超时时间 120s。
location / 实现 SPA 路由，try_files $uri $uri/ /index.html。
静态资源缓存：js/css/png/jpg/jpeg/gif/svg/ico/woff2 等文件设置 7 天缓存，Cache-Control public, immutable。

11.2 多阶段构建

前端 Dockerfile (knowai_frontend/Dockerfile)：
第一阶段 builder：基于 node:20-alpine，工作目录 /app，设置 VITE_API_BASE_URL，配置 npm registry 为阿里云镜像 registry.npmmirror.com，复制 package.json，执行 npm ci，复制源码，执行 npm run build 输出到 /app/dist。
第二阶段：基于 nginx:1.25-alpine，复制 nginx.conf 和 builder 阶段的 dist 目录到 /usr/share/nginx/html，暴露 80 端口。

后端 Dockerfile (knowai_backend/Dockerfile)：
基于 python:3.11-slim，设置 pip 为阿里云镜像 mirrors.aliyun.com/pypi，apt 源替换为 mirrors.aliyun.com。工作目录 /app，复制 requirements.txt，pip install 依赖。预热 tiktoken 编码缓存。复制源码，暴露 8000 端口。使用 gunicorn + uvicorn worker，2 个 worker，超时 120s。

11.3 生产部署

docker-compose.yml 定义 7 个服务：mysql (MySQL 8.0 持久卷)、mongodb (MongoDB 6 持久卷)、redis (Redis 7 AOF 持久化)、elasticsearch (ES 8.10 + IK 分词器)、rabbitmq (预留消息队列)、backend (FastAPI 后端)、frontend (Nginx 前端 + API 代理)。所有服务在 knowai_net 桥接网络上，数据库端口不对外暴露。

数据卷全部声明为 external，需要预先创建。


十二、后台任务系统

任务列表：
秒杀消费者：asyncio.create_task 调度，持续运行，5 个 Worker 监听 Redis 队列
秒杀恢复：asyncio.create_task 调度，每 60 秒执行，恢复崩溃 Worker 的卡住任务
订单过期：asyncio.create_task 调度，每 30 秒执行，取消超时未支付订单
秒杀过期：asyncio.create_task 调度，每 30 秒执行，自动关闭过期秒杀活动
ES 同步：asyncio.create_task 调度，每 60 秒执行，将课程数据同步到 Elasticsearch

订单过期扫描实现 (knowai_backend/app/tasks/order_expire.py)：
无限循环等待 30 秒，创建独立数据库会话。SELECT...FOR UPDATE (skip_locked=True) 查询所有 status=pending 且 expire_time < now 的订单。遍历过期订单，恢复每个 SKU 的库存，将订单状态改为 cancelled。提交事务。


十三、前后端交互模式

13.1 数据流示例（用户浏览课程并购买）

浏览器请求 GET /api/courses -> Nginx 反向代理到 backend:8000 -> FastAPI 查询 MySQL 课程+SKU+秒杀信息 -> 查询 Redis 秒杀库存 -> 返回 JSON 课程列表(含秒杀信息)。

用户选择课程进入详情页 -> 浏览器 GET /api/courses/1 -> FastAPI 查询 MySQL 课程信息+章节+SKU+评价 -> 查询 Redis 秒杀库存 -> 查询 MySQL 是否已购买 -> 返回 CourseDetailRead。

用户下单购买 -> 浏览器 POST /api/orders/create -> FastAPI Redis 分布式锁 + 秒杀库存 -> MySQL 行锁查询+扣库存+创建订单 -> 返回 order_sn 和支付 URL。

13.2 错误处理规范

HTTP 200 成功：前端正常渲染
HTTP 400 参数错误：前端显示具体错误信息
HTTP 401 未认证：前端跳转登录页
HTTP 403 无权限：前端显示"无权限"
HTTP 404 资源不存在：前端显示"未找到"
HTTP 409 冲突：前端显示冲突原因（如"手机号已注册"）
HTTP 422 参数校验失败：前端显示字段校验错误
HTTP 429 限流：前端显示"操作频繁，请稍后重试"
HTTP 500 服务器错误：前端显示"系统异常，请稍后重试"


十四、总结

知学AI 的技术架构具有以下特点：

1. 全异步架构：FastAPI + SQLAlchemy Async + Motor + Redis asyncio，充分利用 Python asyncio 的并发能力。

2. 混合数据存储：根据数据特性选择最合适的存储方案，MySQL 保证事务、Redis 保证高性能、MongoDB 灵活存储。

3. 高并发秒杀：Redis DECR + 异步队列 + 行级锁的三层保障系统，支持大规模并发。

4. AI 智能化：LangChain + LangGraph 多智能体工作流，ChromaDB 向量检索，打造个性化学习体验。

5. 容灾设计：后台 Worker 崩溃恢复、订单超时自动取消、Token 可撤销机制。

6. 容器化部署：Docker Compose 一键部署，开发/生产配置分离，国内镜像源加速。
