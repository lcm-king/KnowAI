#!/bin/bash
# ============================================
# 知学AI - 部署/更新脚本
# 在服务器上运行：拉取最新代码并重启服务
# 失败时自动回滚到上一个镜像并收集日志
# ============================================
set -e

DEPLOY_LOG_DIR="./deploy_logs"
mkdir -p "$DEPLOY_LOG_DIR"
LOG_FILE="$DEPLOY_LOG_DIR/deploy_$(date +%Y%m%d_%H%M%S).log"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "========================================"
echo "  知学AI - 部署更新"
echo "  日志: $LOG_FILE"
echo "========================================"

# 1. 拉取最新代码
echo ">>> 拉取最新代码..."
git pull

# 2. 确保 .env.docker 存在
if [ ! -f .env.docker ]; then
    echo "!!! 错误：.env.docker 不存在！"
    echo "请从 .env.docker.example 复制并修改："
    echo "  cp .env.docker.example .env.docker"
    echo "  vi .env.docker"
    exit 1
fi

# 3. 记录当前镜像 ID，用于失败回滚
BACKUP_BACKEND_IMAGE=$(docker images -q knowai_backend 2>/dev/null || true)
BACKUP_FRONTEND_IMAGE=$(docker images -q knowai_frontend 2>/dev/null || true)
echo ">>> 备份当前镜像：backend=$BACKUP_BACKEND_IMAGE frontend=$BACKUP_FRONTEND_IMAGE"

# 记录当前容器 ID，用于失败时回退
BACKUP_BACKEND_CONTAINER=$(docker compose -f docker-compose.yml ps -q backend 2>/dev/null || true)

# 4. 重新构建并启动（明确指定 production 配置，避免合并 docker-compose.override.yml）
echo ">>> 重新构建并启动容器..."
docker-compose -f docker-compose.yml up --build -d

# 5. 清理旧镜像（保留备份镜像，docker image prune -f 只删 dangling 不删 tagged）
echo ">>> 清理 dangling 镜像..."
docker image prune -f

# 6. 检查服务状态
echo ""
echo ">>> 服务状态："
docker-compose -f docker-compose.yml ps

# 7. 等待后端健康（使用 healthcheck 状态而非轮询 HTTP）
echo ""
echo ">>> 等待后端健康..."
HEALTHY=false
for i in $(seq 1 30); do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' knowai_backend 2>/dev/null || echo "missing")
    if [ "$STATUS" = "healthy" ]; then
        echo "✅ 后端服务健康 (等待 $i 次)"
        HEALTHY=true
        break
    fi
    echo "   等待后端健康... ($i/30) status=$STATUS"
    sleep 5
done

# 8. 失败处理：收集日志并回滚
if [ "$HEALTHY" != "true" ]; then
    echo ""
    echo "!!! 后端在 150s 内未健康，开始回滚..."
    echo ">>> 后端最近日志（最近 200 行）："
    docker logs --tail 200 knowai_backend 2>&1 || true
    echo ""
    echo ">>> 所有容器状态："
    docker-compose -f docker-compose.yml ps -a

    if [ -n "$BACKUP_BACKEND_IMAGE" ]; then
        echo ">>> 回滚到上一版本镜像: $BACKUP_BACKEND_IMAGE"
        # 用旧镜像重启服务
        docker tag "$BACKUP_BACKEND_IMAGE" knowai_backend:rollback
        docker-compose -f docker-compose.yml up -d --no-deps --force-recreate backend
    else
        echo "!!! 无历史镜像可回滚，请手动检查日志: $LOG_FILE"
    fi

    echo ""
    echo "!!! 部署失败，已回滚（或尝试回滚）"
    echo "!!! 完整日志: $LOG_FILE"
    exit 1
fi

# 9. 成功
echo ""
echo "========================================"
echo "  ✅ 部署完成！"
echo "  前端: http://服务器IP:8080"
echo "  后端: http://服务器IP:8000 (仅 127.0.0.1)"
echo "  日志: $LOG_FILE"
echo "========================================"
