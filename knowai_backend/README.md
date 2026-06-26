# KnowAI Backend

FastAPI 后端基础框架，集成 MySQL、MongoDB、Redis、JWT 认证与基础路由。

## 目录结构

```text
knowai_backend/
├── app/
│   ├── init.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── crud/
│   │   └── init.py
│   ├── routers/
│   │   ├── init.py
│   │   ├── auth.py
│   │   └── admin.py
│   └── utils/
│       ├── init.py
│       └── mongo.py
├── .env.example
├── requirements.txt
├── run.py
└── README.md
```

## 快速开始

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

启动后访问：

- API 文档：`http://127.0.0.1:8000/docs`
- 根路径：`http://127.0.0.1:8000/`，返回 `{ "message": "KnowAI API running" }`
- 健康检查：`http://127.0.0.1:8000/api/admin/health`

## 环境变量

复制 `.env.example` 为 `.env`，并按本地环境修改：

- `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` / `MYSQL_DATABASE`：MySQL 连接配置，应用内会拼接为 `mysql+asyncmy` 异步连接串
- `MONGODB_URL`：MongoDB 连接串
- `MONGODB_DB`：MongoDB 数据库名
- `REDIS_URL`：Redis 连接串
- `JWT_SECRET_KEY`：JWT 密钥，生产环境必须修改
- `JWT_ALGORITHM`：JWT 签名算法，默认 `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES`：access token 有效期，默认 10080 分钟（7 天）
- `ALLOWED_ORIGINS`：允许跨域的前端地址 JSON 数组
- `ELASTICSEARCH_HOST` / `ELASTICSEARCH_PORT`：Elasticsearch 服务地址
- `ORDER_EXPIRE_MINUTES`：订单超时时间，默认 30 分钟
- `WEIXIN_APPID` / `WEIXIN_MCHID` / `WEIXIN_KEY`：微信支付配置
- `ALIPAY_APPID` / `ALIPAY_PRIVATE_KEY` / `ALIPAY_PUBLIC_KEY`：支付宝配置
- `NOTIFY_URL`：支付平台异步回调地址
- `PAY_MOCK`：是否启用模拟支付，开发环境默认 `true`
- `DIFY_API_URL`：Dify API 地址，默认 `https://api.dify.ai/v1`
- `DIFY_API_KEY`：Dify 应用 API Key，未配置时 AI 接口返回模拟数据

## 已包含接口

### 认证

- `POST /api/auth/send-code`：发送手机/邮箱验证码，当前模拟打印并返回 `123456`
- `POST /api/auth/register`：校验验证码后注册用户，教师角色会创建待审核讲师资料，并返回 JWT
- `POST /api/auth/login`：用户名/手机号/邮箱 + 密码登录，返回 JWT，同时将 token 状态写入 Redis
- `POST /api/auth/logout`：注销当前 token，从 Redis 删除 token 状态
- `GET /api/auth/me`：获取当前用户，会校验 JWT 签名和 Redis token 状态

### 管理

- `GET /api/admin/health`：基础健康检查，无需认证，返回 `{ "status": "ok" }`
- `GET /api/admin/dashboard`：管理员权限接口，返回模拟统计数据

### 课程

- `GET /api/courses`：公开课程列表，支持分页、分类、关键词和价格排序
- `GET /api/courses/{course_id}`：公开课程详情，包含讲师信息和 SKU
- `GET /api/courses/{course_id}/skus`：公开课程 SKU 列表

### 搜索

- `GET /api/search/courses`：课程搜索，支持关键词、分类、价格区间、排序和标题高亮

### 支付

- `POST /api/pay/create`：创建支付订单，模拟模式返回支付二维码或支付宝跳转信息，并在 5 秒后自动支付成功
- `POST /api/pay/notify`：支付异步回调，验签后更新订单状态并开通课程
- `GET /api/pay/status/{order_sn}`：查询支付状态

### 订单

- `POST /api/orders/create`：创建订单，使用 Redis 分布式锁和 MySQL 行锁扣减库存
- `GET /api/orders`：我的订单列表，支持状态筛选和分页
- `GET /api/orders/{order_sn}`：订单详情
- `POST /api/orders/{order_sn}/cancel`：主动取消 pending 订单并恢复库存

### 学习计划

- `POST /api/cart/add`：添加课程 SKU 到学习计划
- `PUT /api/cart/update`：修改数量或选中状态
- `DELETE /api/cart/remove`：删除一个 SKU
- `DELETE /api/cart/clear`：清空学习计划
- `GET /api/cart`：获取学习计划列表
- `POST /api/cart/merge`：登录后合并本地暂存购物车

### 讲师后台

- `POST /api/teacher/courses`：创建课程
- `PUT /api/teacher/courses/{course_id}`：编辑课程
- `PATCH /api/teacher/courses/{course_id}/submit`：提交课程审核
- `POST /api/teacher/courses/{course_id}/skus`：添加 SKU
- `PUT /api/teacher/skus/{sku_id}`：修改 SKU
- `DELETE /api/teacher/skus/{sku_id}`：下架 SKU
- `GET /api/teacher/courses`：我的课程列表
- `GET /api/teacher/statistics/sales`：销售看板模拟数据

### 秒杀

- `POST /api/seckill/activities`：管理员创建秒杀活动
- `POST /api/seckill/preheat/{activity_id}`：管理员预热活动库存到 Redis，并激活活动
- `POST /api/seckill/{activity_id}`：登录用户参与秒杀，限流后原子扣减 Redis 库存并进入异步队列
- `GET /api/seckill/result/{queue_id}`：轮询秒杀排队结果，成功时返回订单号

### AI 工作流

- `POST /api/ai/generate_quiz`：调用 Dify `quiz_generation` 工作流生成智能题目，未配置 Dify 时返回模拟题目
- `POST /api/ai/recommend_courses`：调用 Dify `course_recommend` 工作流生成个性化课程推荐
- `POST /api/ai/grade_homework`：调用 Dify `homework_grading` 工作流批改作业并返回分数和评语

## 数据库说明

SQLAlchemy 模型包含 `User` 和 `Teacher`，应用启动时会通过 `Base.metadata.create_all` 检查并创建表。

生产环境建议使用 Alembic 管理数据库迁移。

## 支付回调调试

开发时可使用内网穿透暴露本地服务：

```bash
ngrok http 8000
```

将生成的公网地址配置到支付平台回调地址，例如：`https://your-ngrok-domain/api/pay/notify`。
