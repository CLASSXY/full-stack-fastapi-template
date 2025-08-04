FROM python:3.12

ENV PYTHONUNBUFFERED=1

WORKDIR /app/

# 安装PaddleOCR系统依赖
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

# 创建PaddleOCR模型和上传目录
RUN mkdir -p /app/paddleocr_models /app/uploads/ocr

# 设置PaddleOCR环境变量
ENV HUB_HOME=/app/paddleocr_models
ENV PADDLEHUB_HOME=/app/paddleocr_models
# 设置CUDA不可见，强制使用CPU
ENV CUDA_VISIBLE_DEVICES=""

# 复制项目文件
COPY ./scripts /app/scripts
COPY ./alembic.ini /app/
COPY ./app /app/app
COPY ./pyproject.toml ./uv.lock /app/

# 安装基础依赖以避免版本冲突
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    numpy==2.3.2 \
    opencv-python==4.11.0.86 \
    Pillow==11.3.0 \
    setuptools==80.9.0

# 安装PaddlePaddle和OCR依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    paddlepaddle-gpu==2.6.2 \
    paddleocr==3.1.0

# 修改pyproject.toml以使用与本地环境一致的版本组合
RUN sed -i 's/"paddlepaddle-gpu>=2.5.0; sys_platform != '\''darwin'\''",/"paddlepaddle-gpu==2.6.2",/g' /app/pyproject.toml && \
    sed -i 's/"paddlepaddle>=2.5.0; sys_platform == '\''darwin'\''",/"paddlepaddle==3.1.0",/g' /app/pyproject.toml && \
    sed -i 's/"paddleocr>=2.7.0",/"paddleocr==3.1.0",/g' /app/pyproject.toml && \
    sed -i 's/"opencv-python>=4.8.0",/"opencv-python==4.11.0.86",/g' /app/pyproject.toml && \
    sed -i 's/"numpy>=1.21.0",/"numpy==2.3.2",/g' /app/pyproject.toml && \
    sed -i 's/"Pillow>=10.0.0",/"Pillow==11.3.0",/g' /app/pyproject.toml && \
    sed -i 's/"setuptools>=68.0.0",/"setuptools==80.9.0",/g' /app/pyproject.toml && \
    sed -i 's/"sentry-sdk\[fastapi\]>=2.20.0",/"sentry-sdk[fastapi]>=2.20.0",/g' /app/pyproject.toml

# 先安装兼容的 sentry-sdk 版本
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    "sentry-sdk[fastapi]>=2.20.0"

# 安装项目依赖，排除 sentry-sdk 以避免冲突
RUN pip install --no-cache-dir -e . -i https://mirrors.aliyun.com/pypi/simple/ \
    --no-deps

# 安装其他必需的依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    "fastapi[standard]<1.0.0,>=0.114.2" \
    "python-multipart<1.0.0,>=0.0.7" \
    "email-validator<3.0.0.0,>=2.1.0.post1" \
    "passlib[bcrypt]<2.0.0,>=1.7.4" \
    "tenacity<9.0.0,>=8.2.3" \
    "pydantic>2.0" \
    "emails<1.0,>=0.6" \
    "jinja2<4.0.0,>=3.1.4" \
    "alembic<2.0.0,>=1.12.1" \
    "httpx<1.0.0,>=0.25.1" \
    "psycopg[binary]<4.0.0,>=3.1.13" \
    "sqlmodel<1.0.0,>=0.0.21" \
    "bcrypt==3.2.2" \
    "pydantic-settings<3.0.0,>=2.2.1" \
    "pyjwt<3.0.0,>=2.8.0" \
    "aiofiles>=23.0.0" \
    "boto3>=1.26.0" \
    "botocore>=1.29.0" \
    "langchain-ollama>=0.1.0" \
    "langchain-core>=0.1.0"

ENV PYTHONPATH=/app

# 创建monkey patch脚本来修复PaddleOCR的API兼容性问题
RUN echo 'import paddle\ntry:\n    if not hasattr(paddle.base.libpaddle.AnalysisConfig, "set_optimization_level"):\n        paddle.base.libpaddle.AnalysisConfig.set_optimization_level = lambda self, level: None\nexcept Exception as e:\n    print(f"Warning: Could not apply paddle fix: {e}")' > /app/paddle_fix.py

# 创建启动脚本
RUN echo '#!/bin/bash\npython -c "import sys; sys.path.insert(0, \"/app\"); import paddle_fix"\nexec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# 预下载PaddleOCR模型，避免运行时下载
RUN python -c "import sys; sys.path.insert(0, '/app'); import paddle_fix; from paddleocr import PaddleOCR; ocr = PaddleOCR(use_angle_cls=False, lang='ch', use_gpu=False, show_log=False)" || echo "预下载模型失败，将在运行时下载"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["fastapi", "run", "--workers", "4", "app/main.py"]
