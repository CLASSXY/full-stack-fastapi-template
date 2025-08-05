# 前端 Ubuntu 部署指南

本指南将引导您如何在 Ubuntu 服务器上部署您的前端应用程序。我们将使用 Nginx 作为 Web 服务器来托管构建后的静态文件。

## 1. 先决条件

在开始之前，请确保您的 Ubuntu 服务器已经安装了以下软件：

- `git`: 用于从代码仓库拉取最新代码。
- `nginx`: 高性能的 Web 服务器。
- `node.js` 和 `pnpm`: 用于构建前端项目。

### 1.1. 更新系统并安装 Git 和 Nginx

首先，连接到您的 Ubuntu 服务器，并执行以下命令来更新软件包列表并安装 `git` 和 `nginx`：

```bash
sudo apt update
sudo apt install -y git nginx
```

### 1.2. 安装 Node.js 和 pnpm

我们推荐使用 `nvm` (Node Version Manager) 来安装 Node.js，这样可以轻松切换不同的 Node.js 版本。

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# 使 nvm 命令在当前会话中生效
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

# 重新加载 shell 配置
source ~/.bashrc

# 安装 Node.js (推荐使用 LTS 版本)
nvm install --lts

# 安装 pnpm
npm install -g pnpm
```

## 2. 部署步骤

### 2.1. 克隆代码

从您的 Git 仓库中克隆项目的最新代码。

```bash
git clone <您的项目仓库地址>
cd <您的项目目录>/frontend
```
将 `<您的项目仓库地址>` 和 `<您的项目目录>` 替换为实际的 URL 和目录名称。

### 2.2. 安装依赖

进入 `frontend` 目录后，使用 `pnpm` 安装项目所需的所有依赖。

```bash
pnpm install
```

### 2.3. 配置环境变量

前端应用需要知道后端 API 的地址。您需要在 `frontend` 目录下创建一个 `.env.production` 文件来配置生产环境的环境变量。

```bash
nano .env.production
```

在该文件中，添加以下内容，并确保将 URL 替换为您的实际后端服务地址：

```
VITE_API_URL=http://your-backend-api-url.com/api/v1
```

### 2.4. 构建项目

运行构建命令来编译和打包您的前端应用。这会生成一个 `dist` 目录，其中包含了所有优化过的静态文件。

```bash
pnpm run build
```

### 2.5. 配置 Nginx

现在，我们需要配置 Nginx 来托管我们刚刚构建的静态文件。

首先，为您的站点创建一个新的 Nginx 配置文件：

```bash
sudo nano /etc/nginx/sites-available/frontend
```

将以下配置粘贴到文件中。**请务必将 `your_domain.com` 替换为您的域名或服务器的 IP 地址，并将 `/path/to/your/project/frontend/dist` 替换为 `dist` 目录的绝对路径。**

```nginx
server {
    listen 80;
    server_name your_domain.com; # 替换为您的域名或 IP

    # 项目构建后 dist 目录的绝对路径
    root /path/to/your/project/frontend/dist;
    index index.html;

    location / {
        # 这个配置对于单页应用 (SPA) 至关重要
        # 它确保了所有路由都重定向到 index.html，由前端路由处理
        try_files $uri $uri/ /index.html;
    }

    # 可选：添加缓存策略以提高性能
    location ~* \.(?:jpg|jpeg|gif|png|ico|css|js)$ {
        expires 7d;
        add_header Cache-Control "public";
    }
}
```

### 2.6. 启用 Nginx 站点

创建配置文件后，需要通过创建一个符号链接来启用它：

```bash
sudo ln -s /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/
```

在重启 Nginx 之前，最好检查一下配置是否有语法错误：

```bash
sudo nginx -t
```

如果测试成功 (显示 `syntax is ok` 和 `test is successful`)，则可以安全地重启 Nginx 以应用更改：

```bash
sudo systemctl restart nginx
```

## 3. 访问您的应用

部署完成！现在您可以通过浏览器访问您的域名或服务器 IP 地址，应该能看到您的前端应用了。

如果遇到问题，请检查 Nginx 的错误日志：`sudo tail -f /var/log/nginx/error.log`。