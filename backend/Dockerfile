FROM python:3.10

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

# 修改pyproject.toml以使用兼容的版本组合
RUN sed -i 's/"paddlepaddle-gpu>=2.5.0; sys_platform != '\''darwin'\''",/"paddlepaddle==2.6.2",/g' /app/pyproject.toml && \
    sed -i 's/"paddlepaddle>=2.5.0; sys_platform == '\''darwin'\''",//g' /app/pyproject.toml && \
    sed -i 's/"paddleocr>=2.7.0",/"paddleocr==2.8.1",/g' /app/pyproject.toml && \
    sed -i 's/"opencv-python>=4.8.0",/"opencv-python==4.7.1.72",/g' /app/pyproject.toml

# 分步安装依赖以避免版本冲突
# 首先安装核心依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    numpy==1.24.3 \
    opencv-python==4.7.1.72 \
    Pillow==10.0.1

# 然后安装PaddlePaddle
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    paddlepaddle==2.6.2

# 最后安装PaddleOCR
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ \
    paddleocr==2.8.1

# 安装项目依赖
RUN pip install --no-cache-dir -e . -i https://mirrors.aliyun.com/pypi/simple/

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
