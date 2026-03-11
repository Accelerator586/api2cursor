# Git 部署指南（推荐方式）

## 为什么使用 Git 部署？

✅ **版本控制**：可以追踪每次部署的代码版本  
✅ **回滚方便**：出问题可以快速回退到之前的版本  
✅ **团队协作**：多人开发时代码同步更方便  
✅ **CI/CD 集成**：可以配合 GitHub Actions 等实现自动部署  
✅ **代码审查**：通过 Pull Request 进行代码审查  

---

## 部署流程

### 第一步：提交代码到 Git 仓库

#### 1. 初始化 Git 仓库（如果还没有）

```bash
cd /Users/shenhongge/Projects/api2cursor

# 查看当前状态
git status

# 添加所有修改的文件
git add app.py settings.py routes/ utils/ static/ LOGGING.md DEPLOYMENT.md deploy-git.sh

# 提交更改
git commit -m "feat: 添加完整的日志系统

- 实现请求日志收集器（utils/request_logger.py）
- 添加日志查询 API（routes/logs.py）
- 在管理界面添加日志查看标签页
- 支持日志过滤、搜索和导出
- 添加日志配置选项
- 自动清理过期日志
"
```

#### 2. 推送到远程仓库

```bash
# 如果还没有关联远程仓库
git remote add origin https://github.com/yourusername/api2cursor.git

# 推送到远程仓库
git push -u origin main

# 或者如果是其他分支
git push -u origin master
```

#### 3. 验证推送成功

访问你的 GitHub/GitLab 仓库，确认代码已经上传。

---

### 第二步：在服务器上首次部署

#### 1. SSH 登录服务器

```bash
ssh user@your-server-ip
```

#### 2. 克隆代码仓库

```bash
# 进入部署目录
cd /opt  # 或其他你想部署的目录

# 克隆仓库
git clone https://github.com/yourusername/api2cursor.git

# 进入项目目录
cd api2cursor
```

#### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
nano .env
```

填入以下配置：

```bash
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
```

保存并退出（Ctrl+X, Y, Enter）。

#### 4. 运行部署脚本

```bash
# 给脚本执行权限
chmod +x deploy-git.sh

# 执行部署
./deploy-git.sh
```

部署脚本会自动：
- 检查 Docker 环境
- 创建数据目录
- 构建 Docker 镜像
- 启动服务
- 执行健康检查

#### 5. 验证部署

```bash
# 检查服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 测试健康检查
curl http://localhost:3029/health

# 访问管理面板
# 在浏览器打开: http://your-server-ip:3029/admin
```

---

### 第三步：后续更新部署

当你在本地修改代码后，更新线上服务非常简单：

#### 1. 本地提交并推送

```bash
# 在本地开发机器上
cd /Users/shenhongge/Projects/api2cursor

# 查看修改
git status

# 添加修改的文件
git add .

# 提交
git commit -m "fix: 修复某个问题"

# 推送到远程
git push origin main
```

#### 2. 服务器上更新

```bash
# SSH 登录服务器
ssh user@your-server-ip

# 进入项目目录
cd /opt/api2cursor

# 运行部署脚本（会自动拉取最新代码并重新部署）
./deploy-git.sh
```

就这么简单！脚本会自动：
- 拉取最新代码
- 备份现有数据
- 停止旧服务
- 重新构建镜像
- 启动新服务
- 执行健康检查

---

## 高级用法

### 使用分支管理不同环境

```bash
# 开发分支
git checkout -b develop
git push -u origin develop

# 生产分支
git checkout -b production
git push -u origin production

# 在服务器上指定分支部署
BRANCH=production ./deploy-git.sh
```

### 回滚到之前的版本

```bash
# 查看提交历史
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>

# 重新部署
./deploy-git.sh

# 回到最新版本
git checkout main
./deploy-git.sh
```

### 查看部署历史

```bash
# 查看最近的提交
git log --oneline -10

# 查看某次提交的详细信息
git show <commit-hash>

# 查看两个版本之间的差异
git diff <old-commit> <new-commit>
```

---

## 配置 GitHub Actions 自动部署（可选）

创建 `.github/workflows/deploy.yml`：

```yaml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/api2cursor
            ./deploy-git.sh
```

在 GitHub 仓库设置中添加 Secrets：
- `SERVER_HOST`: 服务器 IP
- `SERVER_USER`: SSH 用户名
- `SSH_PRIVATE_KEY`: SSH 私钥

这样每次推送到 main 分支，就会自动部署到服务器！

---

## 最佳实践

### 1. 使用 .gitignore

确保以下文件不被提交：

```gitignore
# 环境变量
.env

# 数据目录
data/

# Python 缓存
__pycache__/
*.pyc
*.pyo
*.pyd

# 开发工具
.vscode/
.idea/
.DS_Store

# 日志
*.log

# 临时文件
*.tmp
*.swp
```

### 2. 保护敏感配置

- ✅ 提交 `.env.example` 作为配置模板
- ❌ 不要提交 `.env` 文件
- ✅ 在服务器上手动创建 `.env`
- ✅ 使用环境变量或密钥管理服务

### 3. 使用标签管理版本

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# 部署特定版本
git checkout v1.0.0
./deploy-git.sh
```

### 4. 代码审查流程

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发完成后推送
git push origin feature/new-feature

# 在 GitHub 上创建 Pull Request
# 审查通过后合并到 main
# 然后在服务器上部署
```

---

## 故障排除

### 问题 1：Git 拉取失败

```bash
# 检查远程仓库连接
git remote -v

# 重新设置远程仓库
git remote set-url origin https://github.com/yourusername/api2cursor.git

# 强制拉取
git fetch --all
git reset --hard origin/main
```

### 问题 2：有本地修改冲突

```bash
# 暂存本地修改
git stash

# 拉取最新代码
git pull

# 恢复本地修改
git stash pop
```

### 问题 3：部署失败

```bash
# 查看详细日志
docker compose logs -f

# 检查配置文件
cat .env

# 手动重新构建
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## 快速命令参考

```bash
# 本地开发
git status                    # 查看状态
git add .                     # 添加所有修改
git commit -m "message"       # 提交
git push                      # 推送

# 服务器部署
cd /opt/api2cursor           # 进入项目目录
./deploy-git.sh              # 一键部署
docker compose logs -f       # 查看日志
docker compose ps            # 查看状态

# 版本管理
git log --oneline            # 查看历史
git checkout <commit>        # 切换版本
git tag v1.0.0              # 创建标签
```

---

## 总结

使用 Git 部署的优势：

1. **简单**：一个命令完成更新部署
2. **安全**：可以随时回滚到之前的版本
3. **可追溯**：每次部署都有记录
4. **协作友好**：团队开发更方便
5. **自动化**：可以集成 CI/CD

推荐的工作流程：

```
本地开发 → Git 提交 → 推送到远程 → 服务器拉取 → 自动部署
```

这是最标准、最专业的部署方式！
