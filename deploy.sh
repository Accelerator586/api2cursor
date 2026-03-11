#!/bin/bash
# 快速部署脚本 - 在线服务器上运行

set -e  # 遇到错误立即退出

echo "=========================================="
echo "API2Cursor 部署脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Docker
echo -e "${YELLOW}[1/6] 检查 Docker 环境...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}错误: Docker Compose 未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境正常${NC}"
echo ""

# 检查 .env 文件
echo -e "${YELLOW}[2/6] 检查配置文件...${NC}"
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}未找到 .env 文件，从 .env.example 创建...${NC}"
        cp .env.example .env
        echo -e "${RED}请编辑 .env 文件，填入正确的配置！${NC}"
        echo "nano .env"
        exit 1
    else
        echo -e "${RED}错误: 未找到 .env 或 .env.example 文件${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ 配置文件存在${NC}"
echo ""

# 创建数据目录
echo -e "${YELLOW}[3/6] 创建数据目录...${NC}"
mkdir -p data/logs
echo -e "${GREEN}✓ 数据目录已创建${NC}"
echo ""

# 停止旧服务
echo -e "${YELLOW}[4/6] 停止旧服务...${NC}"
if docker compose ps | grep -q "Up"; then
    docker compose down
    echo -e "${GREEN}✓ 旧服务已停止${NC}"
else
    echo -e "${GREEN}✓ 没有运行中的服务${NC}"
fi
echo ""

# 构建镜像
echo -e "${YELLOW}[5/6] 构建 Docker 镜像...${NC}"
docker compose build --no-cache
echo -e "${GREEN}✓ 镜像构建完成${NC}"
echo ""

# 启动服务
echo -e "${YELLOW}[6/6] 启动服务...${NC}"
docker compose up -d
echo -e "${GREEN}✓ 服务已启动${NC}"
echo ""

# 等待服务就绪
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 健康检查
echo -e "${YELLOW}执行健康检查...${NC}"
HEALTH_CHECK=$(curl -s http://localhost:3029/health || echo "failed")
if echo "$HEALTH_CHECK" | grep -q "ok"; then
    echo -e "${GREEN}✓ 服务健康检查通过${NC}"
else
    echo -e "${RED}✗ 服务健康检查失败${NC}"
    echo "查看日志: docker compose logs"
    exit 1
fi

echo ""
echo "=========================================="
echo -e "${GREEN}部署完成！${NC}"
echo "=========================================="
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
echo ""
echo "请访问管理面板配置模型映射！"
