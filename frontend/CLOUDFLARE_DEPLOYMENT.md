# Cloudflare Pages 部署指南

本前端项目已配置为支持 Cloudflare Pages 部署。

## 自动部署设置

### 1. 连接 GitHub 仓库到 Cloudflare Pages

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 进入 **Pages** 部分
3. 点击 **Create a project**
4. 连接到 GitHub 并选择你的仓库
5. 设置构建配置：
   - **Framework preset**: `Vite`
   - **Build command**: `npm run build:pages`
   - **Build output directory**: `dist`
   - **Root directory**: `frontend`

### 2. 环境变量配置

在 Cloudflare Pages 项目设置中添加以下环境变量：

#### 生产环境
- `VITE_API_URL`: 你的后端 API 地址（例如：`https://api.yourdomain.com`）

#### 预览环境（可选）
- `VITE_API_URL`: 预览环境的 API 地址

### 3. 自定义域名（可选）

1. 在 Cloudflare Pages 项目设置中
2. 进入 **Custom domains** 部分
3. 添加你的域名
4. 按照说明更新 DNS 记录

## 手动部署

### 使用 Wrangler CLI

1. 安装依赖：
   ```bash
   npm install
   ```

2. 构建项目：
   ```bash
   npm run build
   ```

3. 部署到预览环境：
   ```bash
   npm run deploy:preview
   ```

4. 部署到生产环境：
   ```bash
   npm run deploy:production
   ```

### 首次设置 Wrangler

1. 安装 Wrangler（如果全局安装）：
   ```bash
   npm install -g wrangler
   ```

2. 登录 Cloudflare：
   ```bash
   wrangler login
   ```

3. 创建 Pages 项目：
   ```bash
   wrangler pages project create frontend
   ```

## 项目特性

### SPA 路由支持
- 通过 `_redirects` 文件配置了客户端路由回退
- 所有路由都会回退到 `index.html`

### 缓存优化
- 通过 `_headers` 文件配置了资源缓存
- 静态资源长期缓存
- HTML 文件无缓存确保更新

### 安全头部
- X-Frame-Options
- X-Content-Type-Options
- Referrer-Policy

### 代码分割
- Vendor chunks 分离
- 框架库分离（React, Router, Query, UI）

## 故障排除

### 环境变量问题
确保在 Cloudflare Pages 设置中正确配置了 `VITE_API_URL`。

### 路由问题
如果客户端路由不工作，检查 `_redirects` 文件是否正确部署。

### API 请求问题
检查 CORS 设置，确保后端允许来自 Cloudflare Pages 域名的请求。

### 构建失败
1. 检查 Node.js 版本兼容性
2. 确保所有依赖都在 `package.json` 中
3. 查看构建日志了解具体错误 