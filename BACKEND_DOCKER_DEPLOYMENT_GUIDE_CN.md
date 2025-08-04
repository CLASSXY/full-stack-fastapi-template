🐳 Ubuntu Docker 部署 FastAPI 后端指南

  📋 前置条件

  系统要求

  - Ubuntu 18.04+ (推荐 Ubuntu 22.04 LTS)
  - 最少 2GB 内存，2 CPU 核心
  - 20GB+ 磁盘空间
  - 外部 PostgreSQL 数据库

  🚀 分步部署操作

  1. 准备 Ubuntu 服务器

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

  2. 上传项目文件

  将项目文件上传到服务器（使用 scp、rsync 或 git clone）：

  # 如果使用 git
  git clone <your-repository-url>
  cd full-stack-fastapi-template

  # 或者使用 scp 上传（在本地执行）
  scp -r /Users/xy/Worksapce/full-stack-fastapi-template ubuntu@your-server:/home/ubuntu/

  3. 配置环境变量

  创建生产环境配置文件：

  nano .env.production

  重要配置内容：

  # 基础配置
  DOMAIN=your-server-ip-or-domain
  FRONTEND_HOST=https://your-frontend-domain.com
  ENVIRONMENT=production

  # Docker镜像
  DOCKER_IMAGE_BACKEND=fastapi-backend
  TAG=latest

  # 安全密钥（必须修改！）
  SECRET_KEY=your-super-secret-key-here-minimum-32-characters

  # 初始管理员用户（必须修改！）
  FIRST_SUPERUSER=admin@yourdomain.com
  FIRST_SUPERUSER_PASSWORD=your-secure-admin-password

  # 外部 PostgreSQL 数据库
  POSTGRES_SERVER=your-postgres-server-ip
  POSTGRES_PORT=5432
  POSTGRES_DB=your_database_name
  POSTGRES_USER=your_postgres_user
  POSTGRES_PASSWORD=your_postgres_password

  # CORS 设置
  BACKEND_CORS_ORIGINS="https://your-frontend-domain.com,http://localhost:3000"

  # 邮件设置（可选）
  SMTP_HOST=your-smtp-server.com
  SMTP_USER=your-smtp-user
  SMTP_PASSWORD=your-smtp-password
  EMAILS_FROM_EMAIL=noreply@yourdomain.com

  # OCR和存储设置
  CLOUDFLARE_R2_ACCOUNT_ID=your-r2-account-id
  CLOUDFLARE_R2_ACCESS_KEY_ID=your-r2-access-key
  CLOUDFLARE_R2_SECRET_ACCESS_KEY=your-r2-secret-key
  CLOUDFLARE_R2_BUCKET_NAME=your-bucket-name
  CLOUDFLARE_R2_PUBLIC_URL=https://your-public-url.com

  # 日志级别
  LOG_LEVEL=INFO

  4. 准备数据库

  在外部 PostgreSQL 服务器上创建数据库：

  -- 连接到 PostgreSQL
  psql -h your-postgres-server -U postgres

  -- 创建数据库和用户
  CREATE DATABASE your_database_name;
  CREATE USER your_postgres_user WITH PASSWORD 'your_postgres_password';
  GRANT ALL PRIVILEGES ON DATABASE your_database_name TO your_postgres_user;

  5. 部署后端服务

  使用提供的部署脚本：

  # 检查脚本权限
  chmod +x scripts/backend-only-deploy.sh

  # 部署服务
  ./scripts/backend-only-deploy.sh deploy

  部署脚本会自动：
  - 检查 Docker 和环境配置
  - 构建后端镜像
  - 启动服务容器
  - 执行数据库迁移
  - 显示服务访问地址

  6. 验证部署

  部署成功后，检查服务状态：

  # 查看服务状态
  ./scripts/backend-only-deploy.sh status

  # 查看日志
  ./scripts/backend-only-deploy.sh logs

  # 检查健康状态
  curl http://your-server-ip:9102/api/v1/utils/health-check/

  访问地址：
  - API 文档: http://your-server-ip:9102/docs
  - API 接口: http://your-server-ip:9102/api/v1/
  - 健康检查: http://your-server-ip:9102/api/v1/utils/health-check/

  🔧 管理命令

  # 查看服务状态
  ./scripts/backend-only-deploy.sh status

  # 查看实时日志
  ./scripts/backend-only-deploy.sh logs

  # 重启服务
  ./scripts/backend-only-deploy.sh restart

  # 停止服务
  ./scripts/backend-only-deploy.sh stop

  # 更新部署
  ./scripts/backend-only-deploy.sh update

  # 备份数据库
  ./scripts/backend-only-deploy.sh backup

  # 显示访问地址
  ./scripts/backend-only-deploy.sh urls

  🛡️ 安全配置

  防火墙设置

  # 启用 UFW 防火墙
  sudo ufw enable

  # 允许 SSH
  sudo ufw allow ssh

  # 允许后端端口
  sudo ufw allow 9102

  # 查看防火墙状态
  sudo ufw status

  SSL/HTTPS 配置（推荐）

  如果需要 HTTPS，可以使用 Nginx 反向代理：

  # 安装 Nginx
  sudo apt install nginx -y

  # 配置反向代理（创建配置文件）
  sudo nano /etc/nginx/sites-available/fastapi-backend

  📊 监控和日志

  查看 Docker 容器状态

  docker ps
  docker stats

  查看应用日志

  # 实时日志
  docker logs -f fastapi-backend

  # 查看错误日志
  tail -f backend/logs/error.log

  🚨 故障排除

  常见问题

  1. 容器启动失败
  # 查看详细错误
  docker logs backend-container-name
  2. 数据库连接失败
    - 检查网络连接
    - 确认数据库凭据
    - 检查防火墙设置
  3. OCR 功能异常
    - 确保有足够内存
    - 检查 PaddleOCR 模型下载

  重新部署

  # 停止服务
  ./scripts/backend-only-deploy.sh stop

  # 清理容器和镜像
  docker system prune -a

  # 重新部署
  ./scripts/backend-only-deploy.sh deploy