# 如何在 Ubuntu 上安装 Docker

这个简短的指南将引导您完成在 Ubuntu 系统上安装 Docker 的步骤。

## 安装步骤

请在您的服务器终端中按顺序执行以下命令：

### 1. 更新软件包并安装依赖

```bash
sudo apt-get update

sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```

### 2. 添加 Docker 的官方 GPG 密钥

```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```

### 3. 设置 Docker 的稳定版软件源

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

### 4. 安装 Docker 引擎

```bash
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
```

### 5. （可选但推荐）将当前用户添加到 `docker` 组

这将允许您在不使用 `sudo` 的情况下运行 Docker 命令。

```bash
sudo usermod -aG docker $USER
```

**重要提示**:
为了使组更改生效，您需要注销并重新登录服务器，或者运行 `newgrp docker` 命令。

## 6. 验证安装

安装完成后，运行以下命令来验证 Docker 是否已正确安装并正在运行：

```bash
docker --version
docker run hello-world
```

如果 `hello-world` 容器成功运行，说明您的 Docker 环境已准备就绪。现在您可以重新运行 `deploy-frontend.sh` 脚本了。