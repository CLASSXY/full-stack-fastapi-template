# 🚀 Cloudflare Pages 部署配置

此前端项目已完全配置为支持 Cloudflare Pages 部署。

## 📁 新增文件

### 配置文件
- `wrangler.toml` - Cloudflare Workers/Pages 配置
- `.env.example` - 环境变量示例
- `CLOUDFLARE_DEPLOYMENT.md` - 详细部署指南

### Cloudflare Pages 文件
- `public/_routes.json` - 路由配置
- `public/_redirects` - SPA 重定向规则
- `public/_headers` - HTTP 头部配置

### CI/CD
- `.github/workflows/deploy-frontend.yml` - GitHub Actions 自动部署

## 🔧 修改文件

### package.json
- 添加了 `wrangler` 依赖
- 新增部署脚本：
  - `build:pages` - Cloudflare Pages 构建
  - `deploy:preview` - 预览环境部署
  - `deploy:production` - 生产环境部署

### vite.config.ts
- 优化构建输出
- 添加代码分割策略
- 配置服务器选项

### .gitignore
- 忽略 Cloudflare 相关文件

## 🚀 快速部署

### 方法一：通过 Cloudflare Dashboard（推荐）

1. 访问 [Cloudflare Pages](https://pages.cloudflare.com/)
2. 连接 GitHub 仓库
3. 设置构建配置：
   ```
   框架预设: Vite
   构建命令: npm run build:pages
   构建输出目录: dist
   根目录: frontend
   ```
4. 添加环境变量：`VITE_API_URL`
5. 部署！

### 方法二：使用 GitHub Actions

1. 在 GitHub 仓库设置中添加 Secrets：
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
   - `VITE_API_URL`
2. 推送代码到 `main` 或 `cloudflare` 分支
3. 自动部署！

### 方法三：本地使用 Wrangler

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 登录 Cloudflare
npx wrangler login

# 构建项目
npm run build

# 部署到预览环境
npm run deploy:preview

# 部署到生产环境
npm run deploy:production
```

## 🎯 核心特性

### ✅ SPA 路由支持
- 自动回退到 `index.html`
- 支持 React Router 客户端路由

### ✅ 性能优化
- 静态资源长期缓存
- 代码分割和懒加载
- Gzip 压缩

### ✅ 安全配置
- 安全头部设置
- XSS 保护
- 内容类型保护

### ✅ 开发体验
- 环境变量支持
- 本地预览
- 热重载开发

## 🔑 环境变量

```bash
# .env.local
VITE_API_URL=https://your-api-domain.com
```

## 📚 更多信息

详细部署说明请查看 [CLOUDFLARE_DEPLOYMENT.md](./CLOUDFLARE_DEPLOYMENT.md) 