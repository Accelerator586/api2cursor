#!/bin/sh
# 确保 data 目录可写（挂载的 volume 可能由 root 创建）
mkdir -p /app/data/logs 2>/dev/null
if [ ! -w /app/data ]; then
    echo "[entrypoint] data/ 目录无写入权限，尝试以当前用户运行..."
fi

exec "$@"
