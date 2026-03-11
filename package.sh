#!/bin/bash
# 打包脚本 - 在本地运行，生成部署包

set -e

echo "=========================================="
echo "创建部署包"
echo "=========================================="
echo ""

# 定义要排除的目录和文件
EXCLUDE_PATTERNS=(
    "node_modules"
    ".git"
    "data"
    ".trellis"
    ".claude"
    "__pycache__"
    "*.pyc"
    "*.pyo"
    "*.pyd"
    ".DS_Store"
    ".env"
    "*.tar.gz"
)

# 构建 tar 排除参数
EXCLUDE_ARGS=""
for pattern in "${EXCLUDE_PATTERNS[@]}"; do
    EXCLUDE_ARGS="$EXCLUDE_ARGS --exclude='$pattern'"
done

# 生成文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="api2cursor_${TIMESTAMP}.tar.gz"

echo "正在打包..."
echo "文件名: $PACKAGE_NAME"
echo ""

# 创建压缩包
eval tar -czf "$PACKAGE_NAME" $EXCLUDE_ARGS \
    --exclude="$PACKAGE_NAME" \
    .

# 显示文件大小
SIZE=$(du -h "$PACKAGE_NAME" | cut -f1)
echo "✓ 打包完成！"
echo ""
echo "文件信息:"
echo "  - 文件名: $PACKAGE_NAME"
echo "  - 大小: $SIZE"
echo ""
echo "上传到服务器:"
echo "  scp $PACKAGE_NAME user@your-server:/path/to/deploy/"
echo ""
echo "或使用 rsync (推荐):"
echo "  rsync -avz --progress $PACKAGE_NAME user@your-server:/path/to/deploy/"
