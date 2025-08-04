FROM python:3.12

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

# 安装PaddleOCR和其他必要的系统依赖
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libfontconfig1 \
    libxinerama1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    libasound2 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 为PaddleOCR模型和上传文件创建目录
RUN mkdir -p /app/paddleocr_models /app/uploads/ocr

# 设置PaddleOCR环境变量，确保模型文件存储在正确的位置
ENV HUB_HOME=/app/paddleocr_models
ENV PADDLEHUB_HOME=/app/paddleocr_models
# 强制PaddlePaddle使用CPU，即使在有GPU的系统上
ENV CUDA_VISIBLE_DEVICES=""

# 复制项目依赖定义文件
COPY ./pyproject.toml ./uv.lock /app/

# 在安装依赖前，修改pyproject.toml以强制使用CPU版本的paddlepaddle
# 这是解决在非GPU环境中出现段错误的关键步骤
RUN sed -i "s/\"paddlepaddle-gpu>=2.5.0; sys_platform != 'darwin'\"/\"paddlepaddle>=2.6.0\"/" /app/pyproject.toml

# 复制应用代码
COPY ./scripts /app/scripts
COPY ./alembic.ini /app/
COPY ./app /app/app

# 安装uv，一个更快的pip兼容安装器
RUN pip install --no-cache-dir uv

# 使用uv安装所有项目依赖
# --system-site-packages 选项允许uv安装到系统python环境中
RUN uv pip install --no-cache-dir --system -e .

# 预下载PaddleOCR模型以加快应用启动速度
# PaddleOCR会自动检测环境并选择CPU或GPU。我们通过 ENV CUDA_VISIBLE_DEVICES="" 强制使用CPU。
# use_textline_orientation=False 替换了已弃用的 use_angle_cls
# 移除了不再支持的 show_log 和 use_gpu 参数
RUN python -c "from paddleocr import PaddleOCR; print('正在预下载PaddleOCR模型...'); ocr = PaddleOCR(use_textline_orientation=False, lang='ch'); print('模型下载完成.')"

# 将应用目录添加到PYTHONPATH，以便正确导入模块
ENV PYTHONPATH=/app

# 设置容器启动命令
CMD ["fastapi", "run", "--workers", "4", "app/main.py"]