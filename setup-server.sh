#!/bin/bash
# ============================================
# 知学AI - 服务器首次初始化脚本
# 在阿里云 ECS 上首次运行
# ============================================
set -e

echo "========================================"
echo "  知学AI - 服务器初始化"
echo "========================================"

# 1. 安装 Docker（如未安装）
if ! command -v docker &>/dev/null; then
    echo ">>> 安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo systemctl enable docker
    sudo systemctl start docker
fi

# 2. 安装 Docker Compose（如未安装）
if ! command -v docker-compose &>/dev/null; then
    echo ">>> 安装 Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# 3. 创建 Docker 数据卷
echo ">>> 创建 Docker 数据卷..."
docker volume create knowai_mysql_data 2>/dev/null || true
docker volume create knowai_mongo_data 2>/dev/null || true
docker volume create knowai_redis_data 2>/dev/null || true
docker volume create knowai_es_data 2>/dev/null || true
docker volume create knowai_rabbitmq_data 2>/dev/null || true
docker volume create knowai_uploads_data 2>/dev/null || true

# 4. 配置 ES 虚拟内存（Elasticsearch 需要）
echo ">>> 配置系统参数..."
echo "vm.max_map_count = 262144" | sudo tee /etc/sysctl.d/99-elasticsearch.conf
sudo sysctl -p /etc/sysctl.d/99-elasticsearch.conf

# 5. 防火墙放行端口
echo ">>> 放行端口 80、443..."
sudo firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
sudo firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
sudo firewall-cmd --reload 2>/dev/null || true

echo ""
echo "========================================"
echo "  初始化完成！"
echo "  下一步：配置 .env.docker 然后运行 deploy.sh"
echo "========================================"
