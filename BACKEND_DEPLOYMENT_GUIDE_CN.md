# FastAPI 后端部署指南 - Ubuntu 服务器配合外部 PostgreSQL

本指南将帮助您在 Ubuntu 服务器上使用 Docker 部署 FastAPI 后端服务，配合外部 PostgreSQL 数据库。

## 📋 前置条件

### Ubuntu 服务器要求
- Ubuntu 18.04+ (推荐: Ubuntu 22.04 LTS)
- 最少 2GB 内存，2 CPU 核心
- 20GB+ 磁盘空间
- Root 或 sudo 访问权限

### 外部 PostgreSQL 数据库
- PostgreSQL 12+ 运行在独立服务器上
- 具有完整权限的数据库用户
- 服务器间网络连接
- 防火墙配置允许连接

## 🚀 分步部署

### 1. 准备 Ubuntu 服务器

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 将用户添加到 docker 组
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose-plugin -y

# 重启以应用组更改
sudo reboot
```

### 2. 克隆和设置项目

```bash
# 克隆您的项目
git clone <your-repository-url>
cd full-stack-fastapi-template

# 或者如果不使用 git，通过 SCP/SFTP 上传文件
```

### 3. 配置环境变量

使用您的特定设置编辑 `.env.production` 文件：

```bash
nano .env.production
```

**需要更新的重要配置：**

```env
# 您的域名（替换为实际域名或 IP）
DOMAIN=your-server-ip-or-domain.com
FRONTEND_HOST=https://your-frontend-domain.com

# 安全设置 - 生成新密钥！
SECRET_KEY=your-super-secret-key-here-32-chars-min

# 初始管理员用户配置
# 重要：为您的部署更改这些值
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=your-secure-admin-password

# 外部 PostgreSQL 数据库
POSTGRES_SERVER=your-postgres-server-ip
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password

# 邮件设置（可选但推荐）
SMTP_HOST=your-smtp-server.com
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
EMAILS_FROM_EMAIL=noreply@yourdomain.com

# CORS 源（添加您的前端域名）
BACKEND_CORS_ORIGINS="https://your-frontend-domain.com,http://localhost:3000"
```

### 🔑 配置初始管理员用户

初始超级用户账户在首次部署时自动创建。此账户具有完整的管理权限，通过环境变量进行配置。

#### 修改初始用户凭据

1. **编辑 `.env.production` 文件：**
   ```bash
   nano .env.production
   ```

2. **更新以下变量：**
   ```env
   # 替换为您期望的管理员邮箱
   FIRST_SUPERUSER=your-admin@yourdomain.com
   
   # 替换为强密码
   FIRST_SUPERUSER_PASSWORD=YourSecurePassword123!
   ```

3. **密码要求：**
   - 使用至少 8 个字符的强密码
   - 包含大小写字母
   - 包含数字和特殊字符
   - 避免常见密码或字典词汇

#### 配置示例：
```env
# 管理员用户配置示例
FIRST_SUPERUSER=admin@mycompany.com
FIRST_SUPERUSER_PASSWORD=MySecureAdminPass2024!
```

#### 工作原理：
- 初始用户在应用程序首次启动时自动创建
- 用户创建逻辑位于 `backend/app/core/db.py` 的 `init_db()` 函数中
- 如果指定邮箱的用户已存在，则不会创建新用户
- 用户创建时设置 `is_superuser=True`，获得完整管理访问权限

#### 部署后更改管理员凭据：

如果需要在部署后更改管理员凭据：

1. **选项 1：通过 API（如果您有访问权限）**
   ```bash
   # 使用 API 更新用户凭据
   curl -X PUT "http://your-server-ip:9102/api/v1/users/me" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"email": "new-admin@domain.com", "password": "NewPassword123!"}'
   ```

2. **选项 2：更新环境并重新部署**
   ```bash
   # 使用新凭据更新 .env.production
   nano .env.production
   
   # 重新部署应用程序
   ./scripts/backend-only-deploy.sh update
   ```

3. **选项 3：直接数据库更新（高级）**
   ```bash
   # 连接到您的 PostgreSQL 数据库
   psql -h your-postgres-server -U your-postgres-user -d your_database_name
   
   # 更新用户邮箱
   UPDATE users SET email = 'new-admin@domain.com' WHERE email = 'old-admin@domain.com';
   
   # 注意：密码更新需要适当的哈希处理 - 请使用 API 代替
   ```

#### 安全最佳实践：

1. **首次部署后立即更改默认凭据**
2. **使用环境特定的凭据**（测试/生产环境不同）
3. **安全存储凭据**（生产环境使用密钥管理工具）
4. **启用邮箱验证**（如果配置了 SMTP）
5. **考虑使用 OAuth/SSO**（生产环境）

#### 初始用户创建故障排除：

```bash
# 检查初始用户是否创建成功
docker compose -f docker-compose.backend.yml logs backend | grep -i "superuser\|user"

# 验证用户在数据库中存在
docker compose -f docker-compose.backend.yml exec backend python -c "
from app.core.db import engine
from sqlmodel import Session, select
from app.models import User
with Session(engine) as session:
    user = session.exec(select(User).where(User.email == 'your-admin@domain.com')).first()
    print(f'User found: {user.email if user else \"Not found\"}')"

# 重置并重新创建初始用户（如需要）
docker compose -f docker-compose.backend.yml exec backend python -c "
from app.core.db import engine, init_db
from sqlmodel import Session
with Session(engine) as session:
    init_db(session)"
```

### 4. 生成安全密钥

生成安全的密钥：

```bash
# 生成 SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# 生成安全密码
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(16))"
```

### 5. 测试数据库连接

部署前，测试您的外部数据库连接：

```bash
./scripts/migrate-external-db.sh test
```

### 6. 设置数据库架构

运行数据库迁移并创建初始数据：

```bash
# 运行完整数据库设置
./scripts/migrate-external-db.sh full-setup
```

### 7. 部署后端服务

使用部署脚本部署后端：

```bash
./scripts/backend-only-deploy.sh deploy
```

## 🔧 管理命令

### 日常操作

```bash
# 检查服务状态
./scripts/backend-only-deploy.sh status

# 查看日志
./scripts/backend-only-deploy.sh logs

# 重启服务
./scripts/backend-only-deploy.sh restart

# 停止服务
./scripts/backend-only-deploy.sh stop

# 更新部署
./scripts/backend-only-deploy.sh update
```

### 数据库操作

```bash
# 测试数据库连接
./scripts/migrate-external-db.sh test

# 运行迁移
./scripts/migrate-external-db.sh migrate

# 检查迁移状态
./scripts/migrate-external-db.sh status

# 创建数据库备份
./scripts/backend-only-deploy.sh backup
```

## 🌐 访问您的 API

成功部署后，您的 API 将在以下地址可用：

- **API 基础 URL**: `http://your-server-ip:9102`
- **交互式文档**: `http://your-server-ip:9102/docs`
- **ReDoc**: `http://your-server-ip:9102/redoc`
- **健康检查**: `http://your-server-ip:9102/api/v1/utils/health-check/`

## 🔒 安全考虑

### 1. 防火墙配置

```bash
# 安装 UFW
sudo apt install ufw

# 允许 SSH
sudo ufw allow ssh

# 允许 HTTP 和 HTTPS
sudo ufw allow 80
sudo ufw allow 443

# 允许 API 端口（或使用反向代理）
sudo ufw allow 9102

# 启用防火墙
sudo ufw enable
```

### 2. SSL/TLS 设置（推荐）

对于生产环境，使用 Let's Encrypt 设置 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot

# 获取证书（替换为您的域名）
sudo certbot certonly --standalone -d api.yourdomain.com

# 更新 docker-compose 以使用证书
```

### 3. 反向代理（可选）

考虑使用 Nginx 作为反向代理：

```bash
# 安装 Nginx
sudo apt install nginx

# 配置 Nginx（下面提供示例配置）
```

Nginx 配置示例 (`/etc/nginx/sites-available/fastapi`)：

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:9102;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🐛 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查数据库连接性
   telnet your-postgres-server-ip 5432
   
   # 验证凭据
   ./scripts/migrate-external-db.sh test
   ```

2. **容器无法启动**
   ```bash
   # 检查日志
   docker compose -f docker-compose.backend.yml logs backend
   
   # 检查容器状态
   docker compose -f docker-compose.backend.yml ps
   ```

3. **权限被拒绝**
   ```bash
   # 修复脚本权限
   chmod +x scripts/*.sh
   chmod +x deploy-backend.sh
   ```

4. **端口已被使用**
   ```bash
   # 检查什么在使用端口 9102
   sudo netstat -tulpn | grep :9102
   
   # 如需要，终止进程
   sudo kill -9 <PID>
   ```

### 日志位置

- **应用程序日志**: `docker compose -f docker-compose.backend.yml logs backend`
- **系统日志**: `/var/log/syslog`
- **Docker 日志**: `journalctl -u docker.service`

### 查看 Docker 容器日志

```bash
# 从后端容器查看实时日志
docker compose -f docker-compose.backend.yml logs -f backend

# 查看最后 100 行日志
docker compose -f docker-compose.backend.yml logs --tail=100 backend

# 查看带时间戳的日志
docker compose -f docker-compose.backend.yml logs -t backend

# 查看特定时间的日志
docker compose -f docker-compose.backend.yml logs --since="2024-01-01T00:00:00" backend

# 获取容器 ID 并直接查看日志
docker ps | grep backend
docker logs <container-id>

# 进入运行中的容器检查内部日志
docker compose -f docker-compose.backend.yml exec backend bash

# 在容器内，Python 应用程序日志通常位于：
# - /app/logs/ (如果在应用程序中配置)
# - stdout/stderr (由 Docker 捕获)
# - /var/log/ (容器内系统日志)

# 检查容器内是否有任何日志文件
docker compose -f docker-compose.backend.yml exec backend find /app -name "*.log" -type f
docker compose -f docker-compose.backend.yml exec backend ls -la /var/log/
```

### Python 应用程序日志配置

FastAPI 应用程序日志通常通过几种方式处理：

```bash
# 1. 检查应用程序 stdout/stderr（最常见）
docker compose -f docker-compose.backend.yml logs backend

# 2. 如果应用程序写入日志文件，检查容器内部
docker compose -f docker-compose.backend.yml exec backend ls -la /app/
docker compose -f docker-compose.backend.yml exec backend cat /app/app.log  # 如果存在

# 3. 检查应用程序中的 Python 日志配置
docker compose -f docker-compose.backend.yml exec backend find /app -name "*.py" -exec grep -l "logging" {} \;

# 4. 开发期间实时监控日志
docker compose -f docker-compose.backend.yml logs -f backend | grep -E "(ERROR|WARNING|INFO)"
```

### 日志管理最佳实践

```bash
# 轮转日志以防止磁盘空间问题
# 添加到 crontab 进行日志轮转
0 2 * * * docker system prune -f --filter "until=24h"

# 在 docker-compose.yml 中限制日志大小（添加到服务配置）：
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"

# 将日志导出到外部文件
docker compose -f docker-compose.backend.yml logs backend > backend-logs-$(date +%Y%m%d).log

# 在日志中搜索特定错误
docker compose -f docker-compose.backend.yml logs backend | grep -i "error\|exception\|traceback"
```

## 📊 监控

### 健康检查

API 包含内置健康检查：

```bash
# 检查 API 健康状态
curl http://your-server-ip:9102/api/v1/utils/health-check/

# 检查数据库连接性
curl http://your-server-ip:9102/api/v1/utils/health-check/
```

### 基本监控脚本

创建简单的监控脚本：

```bash
#!/bin/bash
# monitor.sh

API_URL="http://localhost:9102/api/v1/utils/health-check/"

if curl -f -s $API_URL > /dev/null; then
    echo "$(date): API 健康"
else
    echo "$(date): API 宕机 - 正在重启..."
    ./scripts/backend-only-deploy.sh restart
fi
```

添加到 crontab 进行自动监控：

```bash
# 每 5 分钟检查一次
*/5 * * * * /path/to/your/project/monitor.sh >> /var/log/api-monitor.log 2>&1
```

## 🔄 更新和维护

### 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新 Docker 镜像
docker compose -f docker-compose.backend.yml pull

# 更新应用程序
./scripts/backend-only-deploy.sh update
```

### 备份策略

```bash
# 创建自动备份脚本
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
./scripts/backend-only-deploy.sh backup

# 将备份移动到备份目录
mv backup_*.sql $BACKUP_DIR/

# 只保留最近 7 天的备份
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

## 📞 支持

如果遇到问题：

1. 检查日志：`./scripts/backend-only-deploy.sh logs`
2. 验证数据库连接：`./scripts/migrate-external-db.sh test`
3. 检查服务状态：`./scripts/backend-only-deploy.sh status`
4. 查看本指南的常见解决方案

---

**注意**：此部署设置适用于中小规模应用程序。对于高流量生产环境，请考虑额外的优化，如负载均衡、容器编排（Kubernetes）和高级监控解决方案。