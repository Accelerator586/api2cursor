# 部署指南

## 在线服务器部署步骤

### 方法 1: Docker Compose 部署（推荐）

#### 1. 准备服务器环境

```bash
# 确保已安装 Docker 和 Docker Compose
docker --version
docker compose version

# 如果未安装，参考：
# https://docs.docker.com/engine/install/
```

#### 2. 上传代码到服务器

```bash
# 在本地打包代码（排除不必要的文件）
cd /Users/shenhongge/Projects/api2cursor
tar --exclude='node_modules' \
    --exclude='.git' \
    --exclude='data' \
    --exclude='.trellis' \
    --exclude='.claude' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -czf api2cursor.tar.gz .

# 上传到服务器
scp api2cursor.tar.gz user@your-server:/path/to/deploy/

# 或使用 rsync（更高效）
rsync -avz --exclude='node_modules' \
           --exclude='.git' \
           --exclude='data' \
           --exclude='.trellis' \
           --exclude='.claude' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           ./ user@your-server:/path/to/deploy/api2cursor/
```

#### 3. 在服务器上解压并配置

```bash
# SSH 登录服务器
ssh user@your-server

# 解压代码（如果使用 tar）
cd /path/to/deploy
tar -xzf api2cursor.tar.gz -C api2cursor/
cd api2cursor

# 创建环境变量文件
cat > .env << 'EOF'
# 上游中转站配置
PROXY_TARGET_URL=https://your-relay-station.com
PROXY_API_KEY=sk-your-api-key-here

# 服务端口
PROXY_PORT=3029

# 访问鉴权（强烈建议设置）
ACCESS_API_KEY=your-secure-access-key-here

# 请求超时（秒）
API_TIMEOUT=300

# 调试模式（生产环境建议关闭）
DEBUG=false

# CORS 配置（可选，多个用逗号分隔）
# CORS_ALLOWED_ORIGINS=https://your-domain.com

# 速率限制（可选）
# RATE_LIMIT_API=100/minute
# RATE_LIMIT_ADMIN=30/minute
# RATE_LIMIT_LOGIN=5/minute
# RATE_LIMIT_HEALTH=60/minute
EOF

# 设置权限
chmod 600 .env

# 创建数据目录
mkdir -p data/logs
```

#### 4. 构建并启动服务

```bash
# 构建镜像
docker compose build

# 启动服务（后台运行）
docker compose up -d

# 查看日志
docker compose logs -f

# 检查服务状态
docker compose ps
curl http://localhost:3029/health
```

#### 5. 配置反向代理（可选但推荐）

使用 Nginx 作为反向代理，提供 HTTPS 和域名访问：

```nginx
# /etc/nginx/sites-available/api2cursor
server {
    listen 80;
    server_name api.yourdomain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL 证书配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # 代理配置
    location / {
        proxy_pass http://127.0.0.1:3029;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置（适配长时间流式响应）
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/api2cursor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 6. 设置开机自启

Docker Compose 服务已配置 `restart: unless-stopped`，会自动重启。

如需额外保障，可以添加 systemd 服务：

```bash
sudo tee /etc/systemd/system/api2cursor.service << 'EOF'
[Unit]
Description=API2Cursor Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/deploy/api2cursor
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable api2cursor
sudo systemctl start api2cursor
```

---

### 方法 2: 直接运行（不使用 Docker）

#### 1. 安装 Python 环境

```bash
# 安装 Python 3.11+
sudo apt update
sudo apt install python3 python3-pip python3-venv

# 创建虚拟环境
cd /path/to/deploy/api2cursor
python3 -m venv venv
source venv/bin/activate
```

#### 2. 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
# 创建 .env 文件（同上）
nano .env
```

#### 4. 启动服务

```bash
# 前台运行（测试）
python start.py

# 后台运行（使用 nohup）
nohup python start.py > logs/app.log 2>&1 &

# 或使用 systemd（推荐）
sudo tee /etc/systemd/system/api2cursor.service << 'EOF'
[Unit]
Description=API2Cursor Service
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/deploy/api2cursor
Environment="PATH=/path/to/deploy/api2cursor/venv/bin"
ExecStart=/path/to/deploy/api2cursor/venv/bin/python start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable api2cursor
sudo systemctl start api2cursor
sudo systemctl status api2cursor
```

---

## 更新部署

### Docker 方式更新

```bash
# 1. 上传新代码到服务器
cd /Users/shenhongge/Projects/api2cursor
rsync -avz --exclude='node_modules' \
           --exclude='.git' \
           --exclude='data' \
           --exclude='.trellis' \
           --exclude='.claude' \
           ./ user@your-server:/path/to/deploy/api2cursor/

# 2. 在服务器上重新构建
ssh user@your-server
cd /path/to/deploy/api2cursor

# 3. 停止服务
docker compose down

# 4. 重新构建镜像
docker compose build --no-cache

# 5. 启动服务
docker compose up -d

# 6. 查看日志确认
docker compose logs -f
```

### 直接运行方式更新

```bash
# 1. 上传新代码
rsync -avz ... (同上)

# 2. 重启服务
ssh user@your-server
sudo systemctl restart api2cursor
sudo systemctl status api2cursor
```

---

## 监控和维护

### 查看日志

```bash
# Docker 方式
docker compose logs -f
docker compose logs -f --tail=100

# 直接运行方式
sudo journalctl -u api2cursor -f
tail -f logs/app.log

# 查看请求日志（新功能）
ls -lh data/logs/
tail -f data/logs/requests-$(date +%Y-%m-%d).jsonl
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:3029/health

# 检查管理面板
curl -I http://localhost:3029/admin

# 检查模型列表
curl http://localhost:3029/v1/models
```

### 磁盘空间管理

```bash
# 查看日志文件大小
du -sh data/logs/

# 手动清理旧日志（超过 30 天）
find data/logs -name "requests-*.jsonl" -mtime +30 -delete

# 清理 Docker 镜像和容器
docker system prune -a
```

### 备份配置

```bash
# 备份配置文件
tar -czf backup-$(date +%Y%m%d).tar.gz \
    .env \
    data/settings.json \
    data/logs/

# 恢复配置
tar -xzf backup-20260311.tar.gz
```

---

## 故障排除

### 服务无法启动

```bash
# 检查端口占用
sudo netstat -tlnp | grep 3029
sudo lsof -i :3029

# 检查 Docker 日志
docker compose logs

# 检查环境变量
docker compose config
```

### 无法访问管理面板

1. 检查防火墙规则
2. 检查 ACCESS_API_KEY 是否正确
3. 检查 Nginx 配置（如果使用）
4. 查看浏览器控制台错误

### 请求失败

1. 查看请求日志：管理面板 → 日志标签页
2. 检查上游 API 配置
3. 检查模型映射配置
4. 查看服务器日志

### 性能问题

```bash
# 查看资源使用
docker stats

# 调整 Docker 资源限制（compose.yml）
mem_limit: 1g
cpus: 2.0

# 优化日志配置
# 在管理面板中关闭请求/响应内容记录
```

---

## 安全建议

1. **必须设置 ACCESS_API_KEY**：防止未授权访问
2. **使用 HTTPS**：通过 Nginx 反向代理配置 SSL
3. **限制访问 IP**：在防火墙或 Nginx 中配置白名单
4. **定期更新**：及时更新依赖和系统补丁
5. **监控日志**：定期检查异常访问
6. **备份配置**：定期备份 data 目录

---

## 快速命令参考

```bash
# 启动服务
docker compose up -d

# 停止服务
docker compose down

# 重启服务
docker compose restart

# 查看日志
docker compose logs -f

# 重新构建
docker compose build --no-cache

# 进入容器
docker compose exec api2cursor sh

# 查看资源使用
docker stats

# 清理
docker compose down -v
docker system prune -a
```
