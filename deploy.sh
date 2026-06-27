#!/bin/bash
# ============================================
# 知学AI - 部署/更新脚本
# 在服务器上运行：拉取最新代码并重启服务
# ============================================
set -e

echo "========================================"
echo "  知学AI - 部署更新"
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

# 3. 重新构建并启动
echo ">>> 重新构建并启动容器..."
docker-compose up --build -d

# 4. 清理旧镜像
echo ">>> 清理旧镜像..."
docker image prune -f

# 5. 检查服务状态
echo ""
echo ">>> 服务状态："
docker-compose ps

# 6. 等待后端启动并检查健康
echo ""
echo ">>> 等待后端就绪..."
sleep 5
for i in $(seq 1 12); do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs 2>/dev/null || echo "000")
    if [ "$STATUS" = "200" ]; then
        echo "✅ 后端服务正常 (HTTP $STATUS)"
        break
    fi
    echo "   等待后端启动... ($i/12)"
    sleep 5
done

echo ""
echo "========================================"
echo "  部署完成！"
echo "  前端: http://服务器IP:8080"
echo "  后端: http://服务器IP:8000"
echo "========================================"
