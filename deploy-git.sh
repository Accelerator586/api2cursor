#!/bin/bash
# Git 部署脚本 - 在服务器上运行

set -e

echo "=========================================="
echo "API2Cursor Git 部署脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
REPO_URL="${REPO_URL:-https://github.com/yourusername/api2cursor.git}"
BRANCH="${BRANCH:-main}"
DEPLOY_DIR="${DEPLOY_DIR:-$(pwd)}"

# 检查是否在 Git 仓库中
if [ ! -d .git ]; then
    echo -e "${RED}错误: 当前目录不是 Git 仓库${NC}"
    echo "首次部署请运行:"
    echo "  git clone $REPO_URL"
    echo "  cd api2cursor"
    echo "  ./deploy-git.sh"
    exit 1
fi

# 1. 拉取最新代码
echo -e "${YELLOW}[1/7] 拉取最新代码...${NC}"
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
LATEST_COMMIT=$(git rev-parse origin/$BRANCH)

if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    echo -e "${GREEN}✓ 代码已是最新版本${NC}"
else
    echo "当前版本: ${CURRENT_COMMIT:0:8}"
    echo "最新版本: ${LATEST_COMMIT:0:8}"
    git pull origin $BRANCH
    echo -e "${GREEN}✓ 代码已更新${NC}"
fi
echo ""

# 2. 检查 Docker 环境
echo -e "${YELLOW}[2/7] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    exit 1
fi
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 环境正常${NC}"
echo ""

# 3. 检查配置文件
echo -e "${YELLOW}[3/7] 检查配置文件...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}未找到 .env 文件，从 .env.example 创建...${NC}"
        cp .env.example .env
        echo -e "${RED}请编辑 .env 文件，填入正确的配置！${NC}"
        echo "nano .env"
        exit 1
    else
        echo -e "${RED}错误: 未找到 .env 文件${NC}"
        exit 1
    fi
fi
echo -e "${GREEN}✓ 配置文件存在${NC}"
echo ""

# 4. 备份数据（如果存在）
echo -e "${YELLOW}[4/7] 备份数据...${NC}"
if [ -d data ]; then
    BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    cp -r data "$BACKUP_DIR/"
    echo -e "${GREEN}✓ 数据已备份到 $BACKUP_DIR${NC}"
else
    mkdir -p data/logs
    echo -e "${GREEN}✓ 创建数据目录${NC}"
fi
echo ""

# 5. 停止旧服务
echo -e "${YELLOW}[5/7] 停止旧服务...${NC}"
if docker compose ps | grep -q "Up"; then
    docker compose down
    echo -e "${GREEN}✓ 旧服务已停止${NC}"
else
    echo -e "${GREEN}✓ 没有运行中的服务${NC}"
fi
echo ""

# 6. 构建新镜像
echo -e "${YELLOW}[6/7] 构建 Docker 镜像...${NC}"
docker compose build --no-cache
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 7. 启动服务
echo -e "${YELLOW}[7/7] 启动服务...${NC}"
docker compose up -d
echo -e "${GREEN}✓ 服务已启动${NC}"
echo ""

# 等待服务就绪
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 健康检查
echo -e "${YELLOW}执行健康检查...${NC}"
MAX_RETRIES=10
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    HEALTH_CHECK=$(curl -s http://localhost:3029/health 2>/dev/null || echo "failed")
    if echo "$HEALTH_CHECK" | grep -q "ok"; then
        echo -e "${GREEN}✓ 服务健康检查通过${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}✗ 服务健康检查失败${NC}"
        echo "查看日志: docker compose logs"
        exit 1
    fi
    echo "重试 $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
echo ""
echo "部署信息:"
echo "  - Git 分支: $BRANCH"
echo "  - 提交版本: ${LATEST_COMMIT:0:8}"
echo "  - 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""
echo "服务信息:"
echo "  - 健康检查: http://localhost:3029/health"
echo "  - 管理面板: http://localhost:3029/admin"
echo "  - 模型列表: http://localhost:3029/v1/models"
echo ""
echo "常用命令:"
echo "  - 查看日志: docker compose logs -f"
echo "  - 查看状态: docker compose ps"
echo "  - 重启服务: docker compose restart"
echo "  - 停止服务: docker compose down"
echo "  - 更新部署: ./deploy-git.sh"
echo ""
