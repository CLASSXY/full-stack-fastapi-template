# 前端 Docker 部署指南

本指南将指导您如何使用 Docker 在任何环境中部署您的前端应用程序。

## 1. 先决条件

在开始之前，请确保您的系统上已经安装了 [Docker](https://www.docker.com/)。

## 2. 部署步骤

### 2.1. 构建 Docker 镜像

在您的项目根目录中，打开终端并运行以下命令来构建 Docker 镜像。

**重要提示**:
- 将 `<your-image-name>` 替换为您想要的镜像名称（例如 `my-frontend-app`）。
- 将 `http://your-backend-api-url.com/api/v1` 替换为您的实际后端 API 地址。这个地址会通过 `VITE_API_URL` 构建参数传递给 Dockerfile。

```bash
docker build \
  --build-arg "VITE_API_URL=http://your-backend-api-url.com/api/v1" \
  -t <your-image-name> \
  -f frontend/Dockerfile .
```

这个命令会：
1.  使用 `frontend/Dockerfile` 文件。
2.  在构建过程中设置 `VITE_API_URL` 环境变量。
3.  创建一个名为 `<your-image-name>` 的新 Docker 镜像。

### 2.2. 运行 Docker 容器

镜像构建成功后，使用以下命令来运行一个容器：

```bash
docker run -d -p 8080:80 --name <your-container-name> <your-image-name>
```

这个命令会：
- `-d`: 在后台（detached mode）运行容器。
- `-p 8080:80`: 将主机的 8080 端口映射到容器的 80 端口。这意味着您可以通过访问主机的 8080 端口来访问您的应用。您可以根据需要更改主机端口。
- `--name <your-container-name>`: 为您的容器指定一个名称，方便管理。
- `<your-image-name>`: 指定要运行的镜像。

## 3. 访问您的应用

部署完成！现在您可以通过浏览器访问 `http://localhost:8080` (或者您服务器的 `http://<服务器IP>:8080`) 来查看您的前端应用。

## 4. 常用 Docker 命令

- **查看正在运行的容器**:
  ```bash
  docker ps
  ```
- **停止容器**:
  ```bash
  docker stop <your-container-name>
  ```
- **启动已停止的容器**:
  ```bash
  docker start <your-container-name>
  ```
- **查看容器日志**:
  ```bash
  docker logs -f <your-container-name>
  ```
- **删除容器** (需要先停止):
  ```bash
  docker rm <your-container-name>
  ```
- **删除镜像**:
  ```bash
  docker rmi <your-image-name>