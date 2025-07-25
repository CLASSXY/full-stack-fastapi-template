# FastAPI Backend Deployment Guide - Ubuntu Server with External PostgreSQL

This guide will help you deploy only the FastAPI backend service on an Ubuntu server using Docker, with an external PostgreSQL database.

## 📋 Prerequisites

### Ubuntu Server Requirements
- Ubuntu 18.04+ (recommended: Ubuntu 22.04 LTS)
- Minimum 2GB RAM, 2 CPU cores
- 20GB+ disk space
- Root or sudo access

### External PostgreSQL Database
- PostgreSQL 12+ running on a separate server
- Database user with full privileges
- Network connectivity between servers
- Firewall configured to allow connections

## 🚀 Step-by-Step Deployment

### 1. Prepare Ubuntu Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Reboot to apply group changes
sudo reboot
```

### 2. Clone and Setup Project

```bash
# Clone your project
git clone <your-repository-url>
cd full-stack-fastapi-template

# Or upload files via SCP/SFTP if not using git
```

### 3. Configure Environment Variables

Edit the `.env.production` file with your specific settings:

```bash
nano .env.production
```

**Important configurations to update:**

```env
# Your domain (replace with actual domain or IP)
DOMAIN=your-server-ip-or-domain.com
FRONTEND_HOST=https://your-frontend-domain.com

# Security - GENERATE NEW KEYS!
SECRET_KEY=your-super-secret-key-here-32-chars-min

# Initial Admin User Configuration
# IMPORTANT: Change these values for your deployment
FIRST_SUPERUSER=admin@yourdomain.com
FIRST_SUPERUSER_PASSWORD=your-secure-admin-password

# External PostgreSQL Database
POSTGRES_SERVER=your-postgres-server-ip
POSTGRES_PORT=5432
POSTGRES_DB=your_database_name
POSTGRES_USER=your_postgres_user
POSTGRES_PASSWORD=your_postgres_password

# Email settings (optional but recommended)
SMTP_HOST=your-smtp-server.com
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
EMAILS_FROM_EMAIL=noreply@yourdomain.com

# CORS origins (add your frontend domains)
BACKEND_CORS_ORIGINS="https://your-frontend-domain.com,http://localhost:3000"
```

### 🔑 Configuring Initial Admin User

The initial superuser account is automatically created during the first deployment. This account has full administrative privileges and is configured through environment variables.

#### Modifying Initial User Credentials

1. **Edit the `.env.production` file:**
   ```bash
   nano .env.production
   ```

2. **Update the following variables:**
   ```env
   # Replace with your desired admin email
   FIRST_SUPERUSER=your-admin@yourdomain.com
   
   # Replace with a strong password
   FIRST_SUPERUSER_PASSWORD=YourSecurePassword123!
   ```

3. **Password Requirements:**
   - Use a strong password with at least 8 characters
   - Include uppercase and lowercase letters
   - Include numbers and special characters
   - Avoid common passwords or dictionary words

#### Example Configuration:
```env
# Example admin user configuration
FIRST_SUPERUSER=admin@mycompany.com
FIRST_SUPERUSER_PASSWORD=MySecureAdminPass2024!
```

#### How It Works:
- The initial user is created automatically when the application starts for the first time
- The user creation logic is in `backend/app/core/db.py` in the `init_db()` function
- If a user with the specified email already exists, no new user is created
- The user is created with `is_superuser=True`, giving full administrative access

#### Changing Admin Credentials After Deployment:

If you need to change the admin credentials after deployment:

1. **Option 1: Through the API (if you have access)**
   ```bash
   # Use the API to update user credentials
   curl -X PUT "http://your-server-ip:9102/api/v1/users/me" \
        -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"email": "new-admin@domain.com", "password": "NewPassword123!"}'
   ```

2. **Option 2: Update environment and redeploy**
   ```bash
   # Update .env.production with new credentials
   nano .env.production
   
   # Redeploy the application
   ./scripts/backend-only-deploy.sh update
   ```

3. **Option 3: Direct database update (advanced)**
   ```bash
   # Connect to your PostgreSQL database
   psql -h your-postgres-server -U your-postgres-user -d your_database_name
   
   # Update user email
   UPDATE users SET email = 'new-admin@domain.com' WHERE email = 'old-admin@domain.com';
   
   # Note: Password updates require proper hashing - use the API instead
   ```

#### Security Best Practices:

1. **Change default credentials immediately after first deployment**
2. **Use environment-specific credentials** (different for staging/production)
3. **Store credentials securely** (use secrets management tools in production)
4. **Enable email verification** if SMTP is configured
5. **Consider using OAuth/SSO** for production environments

#### Troubleshooting Initial User Creation:

```bash
# Check if the initial user was created successfully
docker compose -f docker-compose.backend.yml logs backend | grep -i "superuser\|user"

# Verify user exists in database
docker compose -f docker-compose.backend.yml exec backend python -c "
from app.core.db import engine
from sqlmodel import Session, select
from app.models import User
with Session(engine) as session:
    user = session.exec(select(User).where(User.email == 'your-admin@domain.com')).first()
    print(f'User found: {user.email if user else \"Not found\"}')"

# Reset and recreate initial user (if needed)
docker compose -f docker-compose.backend.yml exec backend python -c "
from app.core.db import engine, init_db
from sqlmodel import Session
with Session(engine) as session:
    init_db(session)"
```

### 4. Generate Secure Keys

Generate secure secret keys:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"

# Generate secure passwords
python3 -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(16))"
```

### 5. Test Database Connection

Before deploying, test your external database connection:

```bash
./scripts/migrate-external-db.sh test
```

### 6. Setup Database Schema

Run database migrations and create initial data:

```bash
# Run full database setup
./scripts/migrate-external-db.sh full-setup
```

### 7. Deploy Backend Service

Deploy the backend using the deployment script:

```bash
./scripts/backend-only-deploy.sh deploy
```

## 🔧 Management Commands

### Daily Operations

```bash
# Check service status
./scripts/backend-only-deploy.sh status

# View logs
./scripts/backend-only-deploy.sh logs

# Restart services
./scripts/backend-only-deploy.sh restart

# Stop services
./scripts/backend-only-deploy.sh stop

# Update deployment
./scripts/backend-only-deploy.sh update
```

### Database Operations

```bash
# Test database connection
./scripts/migrate-external-db.sh test

# Run migrations
./scripts/migrate-external-db.sh migrate

# Check migration status
./scripts/migrate-external-db.sh status

# Create database backup
./scripts/backend-only-deploy.sh backup
```

## 🌐 Access Your API

After successful deployment, your API will be available at:

- **API Base URL**: `http://your-server-ip:9102`
- **Interactive Docs**: `http://your-server-ip:9102/docs`
- **ReDoc**: `http://your-server-ip:9102/redoc`
- **Health Check**: `http://your-server-ip:9102/api/v1/utils/health-check/`

## 🔒 Security Considerations

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw

# Allow SSH
sudo ufw allow ssh

# Allow HTTP and HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow API port (or use reverse proxy)
sudo ufw allow 9102

# Enable firewall
sudo ufw enable
```

### 2. SSL/TLS Setup (Recommended)

For production, set up SSL certificates using Let's Encrypt:

```bash
# Install Certbot
sudo apt install certbot

# Get certificate (replace with your domain)
sudo certbot certonly --standalone -d api.yourdomain.com

# Update docker-compose to use certificates
```

### 3. Reverse Proxy (Optional)

Consider using Nginx as a reverse proxy:

```bash
# Install Nginx
sudo apt install nginx

# Configure Nginx (example config provided below)
```

Example Nginx configuration (`/etc/nginx/sites-available/fastapi`):

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

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database connectivity
   telnet your-postgres-server-ip 5432
   
   # Verify credentials
   ./scripts/migrate-external-db.sh test
   ```

2. **Container Won't Start**
   ```bash
   # Check logs
   docker compose -f docker-compose.backend.yml logs backend
   
   # Check container status
   docker compose -f docker-compose.backend.yml ps
   ```

3. **Permission Denied**
   ```bash
   # Fix script permissions
   chmod +x scripts/*.sh
   chmod +x deploy-backend.sh
   ```

4. **Port Already in Use**
   ```bash
   # Check what's using port 9102
   sudo netstat -tulpn | grep :9102
   
   # Kill process if needed
   sudo kill -9 <PID>
   ```

### Log Locations

- **Application logs**: `docker compose -f docker-compose.backend.yml logs backend`
- **System logs**: `/var/log/syslog`
- **Docker logs**: `journalctl -u docker.service`

### Viewing Docker Container Logs

```bash
# View real-time logs from the backend container
docker compose -f docker-compose.backend.yml logs -f backend

# View last 100 lines of logs
docker compose -f docker-compose.backend.yml logs --tail=100 backend

# View logs with timestamps
docker compose -f docker-compose.backend.yml logs -t backend

# View logs from a specific time
docker compose -f docker-compose.backend.yml logs --since="2024-01-01T00:00:00" backend

# Get container ID and view logs directly
docker ps | grep backend
docker logs <container-id>

# Enter the running container to check internal logs
docker compose -f docker-compose.backend.yml exec backend bash

# Inside the container, Python application logs are typically located at:
# - /app/logs/ (if configured in the application)
# - stdout/stderr (captured by Docker)
# - /var/log/ (system logs inside container)

# Check if there are any log files inside the container
docker compose -f docker-compose.backend.yml exec backend find /app -name "*.log" -type f
docker compose -f docker-compose.backend.yml exec backend ls -la /var/log/
```

### Python Application Log Configuration

The FastAPI application logs are typically handled in several ways:

```bash
# 1. Check application stdout/stderr (most common)
docker compose -f docker-compose.backend.yml logs backend

# 2. If the app writes to log files, check inside container
docker compose -f docker-compose.backend.yml exec backend ls -la /app/
docker compose -f docker-compose.backend.yml exec backend cat /app/app.log  # if exists

# 3. Check Python logging configuration in the application
docker compose -f docker-compose.backend.yml exec backend find /app -name "*.py" -exec grep -l "logging" {} \;

# 4. Monitor logs in real-time during development
docker compose -f docker-compose.backend.yml logs -f backend | grep -E "(ERROR|WARNING|INFO)"
```

### Log Management Best Practices

```bash
# Rotate logs to prevent disk space issues
# Add to crontab for log rotation
0 2 * * * docker system prune -f --filter "until=24h"

# Limit log size in docker-compose.yml (add to service configuration):
# logging:
#   driver: "json-file"
#   options:
#     max-size: "10m"
#     max-file: "3"

# Export logs to external file
docker compose -f docker-compose.backend.yml logs backend > backend-logs-$(date +%Y%m%d).log

# Search for specific errors in logs
docker compose -f docker-compose.backend.yml logs backend | grep -i "error\|exception\|traceback"
```

## 📊 Monitoring

### Health Checks

The API includes built-in health checks:

```bash
# Check API health
curl http://your-server-ip:9102/api/v1/utils/health-check/

# Check database connectivity
curl http://your-server-ip:9102/api/v1/utils/health-check/
```

### Basic Monitoring Script

Create a simple monitoring script:

```bash
#!/bin/bash
# monitor.sh

API_URL="http://localhost:9102/api/v1/utils/health-check/"

if curl -f -s $API_URL > /dev/null; then
    echo "$(date): API is healthy"
else
    echo "$(date): API is down - restarting..."
    ./scripts/backend-only-deploy.sh restart
fi
```

Add to crontab for automatic monitoring:

```bash
# Check every 5 minutes
*/5 * * * * /path/to/your/project/monitor.sh >> /var/log/api-monitor.log 2>&1
```

## 🔄 Updates and Maintenance

### Regular Updates

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Docker images
docker compose -f docker-compose.backend.yml pull

# Update application
./scripts/backend-only-deploy.sh update
```

### Backup Strategy

```bash
# Create automated backup script
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
./scripts/backend-only-deploy.sh backup

# Move backup to backup directory
mv backup_*.sql $BACKUP_DIR/

# Keep only last 7 days of backups
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

## 📞 Support

If you encounter issues:

1. Check the logs: `./scripts/backend-only-deploy.sh logs`
2. Verify database connection: `./scripts/migrate-external-db.sh test`
3. Check service status: `./scripts/backend-only-deploy.sh status`
4. Review this guide for common solutions

---

**Note**: This deployment setup is suitable for small to medium-scale applications. For high-traffic production environments, consider additional optimizations like load balancing, container orchestration (Kubernetes), and advanced monitoring solutions.