# KnowAI Docker 部署说明

## 文件清单

- `docker-compose.yml`：编排 MySQL、MongoDB、Redis、Elasticsearch、RabbitMQ、后端、前端
- `.env.docker`：Docker 环境变量示例
- `start.sh`：一键启动脚本
- `knowai_backend/Dockerfile`：后端生产镜像，使用 gunicorn + uvicorn workers
- `knowai_backend/.dockerignore`：后端构建忽略文件
- `knowai_frontend/Dockerfile`：前端多阶段构建镜像
- `knowai_frontend/nginx.conf`：前端 Nginx 静态托管与 `/api` 反向代理
- `knowai_frontend/.dockerignore`：前端构建忽略文件

## 服务清单

| 服务 | 镜像/构建 | 容器名 | 说明 |
| --- | --- | --- | --- |
| mysql | `mysql:8.0` | `knowai_mysql` | 业务关系型数据库 |
| mongodb | `mongo:6` | `knowai_mongodb` | 用户行为、扩展数据 |
| redis | `redis:7-alpine` | `knowai_redis` | JWT 状态、购物车、秒杀队列与缓存 |
| elasticsearch | `elasticsearch:8.10.2` | `knowai_elasticsearch` | 课程搜索 |
| rabbitmq | `rabbitmq:3-management` | `knowai_rabbitmq` | 消息队列预留 |
| backend | 本地构建 | `knowai_backend` | FastAPI API 服务 |
| frontend | 本地构建 | `knowai_frontend` | Nginx 托管 Vue 静态文件并代理 API |

所有服务都加入 `knowai_net` 网络，通过容器名互相访问。

## 启动

先根据实际生产环境修改 `.env.docker` 中的密码、JWT 密钥、支付密钥和 Dify Key。

```bash
chmod +x start.sh
./start.sh
```

或直接运行：

```bash
docker compose --env-file .env.docker up -d --build
```

访问：

- 前端：`http://localhost/`
- 后端 API：`http://localhost:8000/`
- API 文档：`http://localhost:8000/docs`

## 初始化

后端启动时会在 FastAPI lifespan 中执行：

- `init_db()`：自动创建 MySQL 表
- `init_mongo()`：创建 MongoDB 索引
- `init_redis()`：初始化 Redis 连接

Elasticsearch 索引可在服务启动后手动执行：

```bash
docker compose --env-file .env.docker exec backend python init_es.py
```

## 数据持久化

Compose 已配置以下 Docker volumes：

- `mysql_data`
- `mongo_data`
- `redis_data`
- `es_data`
- `rabbitmq_data`

删除容器不会删除数据卷。如需清空所有数据，需谨慎执行：

```bash
docker compose --env-file .env.docker down -v
```

## 生产注意事项

1. 必须修改 `.env.docker` 中的默认密码和 `JWT_SECRET_KEY`。
2. 当前 Elasticsearch 关闭了 `xpack.security.enabled`，正式公网部署应开启鉴权或只允许内网访问。
3. Compose 中仅暴露 `80` 和 `8000`，数据库、Redis、ES、RabbitMQ 不映射宿主端口。
4. 后端使用：

```bash
gunicorn app.main:app -k uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000 --timeout 120
```

5. 前端镜像使用 Node 构建 `dist`，再由 Nginx 托管静态文件。
6. 前端容器内 Nginx 会将 `/api/` 代理到 `http://backend:8000/api/`。
7. 若部署到真实域名，请更新 `.env.docker` 中的 `ALLOWED_ORIGINS` 和 `NOTIFY_URL`。

## 常用命令

```bash
# 查看服务状态
docker compose --env-file .env.docker ps

# 查看日志
docker compose --env-file .env.docker logs -f backend

docker compose --env-file .env.docker logs -f frontend

# 重启后端
docker compose --env-file .env.docker restart backend

# 停止服务
docker compose --env-file .env.docker down
```
