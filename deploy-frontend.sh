#!/bin/bash

# --- 检查 Docker 是否安装 ---
if ! [ -x "$(command -v docker)" ]; then
  echo '错误: Docker 未安装。' >&2
  echo '请先在您的服务器上安装 Docker，然后再运行此脚本。' >&2
  exit 1
fi

# --- 配置 ---
# Docker 镜像和容器的名称
IMAGE_NAME="full-stack-fastapi-template-frontend"
CONTAINER_NAME="full-stack-fastapi-template-frontend"

# 后端 API 地址
# 重要提示：请确保此地址可以从 Docker 构建环境和最终运行环境中访问
API_URL="http://192.168.110.244:9102"

# 要映射到主机的端口
HOST_PORT=8888

# --- 部署脚本 ---

echo "--- 开始部署前端应用 ---"
set -e # 如果任何命令失败，则立即退出

# 1. 停止并删除同名的旧容器 (如果存在)
echo "=> 正在停止并删除旧容器..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 2. 构建新的 Docker 镜像
echo "=> 正在构建 Docker 镜像: $IMAGE_NAME"
echo "   使用 API 地址: $API_URL"
docker build \
  --build-arg "VITE_API_URL=${API_URL}" \
  -t $IMAGE_NAME \
  -f frontend/Dockerfile .

# 3. 运行新的 Docker 容器
echo "=> 正在运行新的 Docker 容器: $CONTAINER_NAME"
docker run -d -p ${HOST_PORT}:80 --name $CONTAINER_NAME $IMAGE_NAME

echo ""
echo "--- 部署成功！ ---"
echo "您的应用正在运行，可以通过以下地址访问:"
echo "http://localhost:${HOST_PORT}"
echo "或者 http://<您的服务器IP>:${HOST_PORT}"