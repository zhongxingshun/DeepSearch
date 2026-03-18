# DeepSearch 后端 Dockerfile
# 版本: v1.0

# ================================
# 构建阶段: 安装依赖
# ================================
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ================================
# 运行阶段: 最小化镜像
# ================================
FROM python:3.11-slim as runtime

LABEL maintainer="DeepSearch Team"
LABEL version="1.0"
LABEL description="DeepSearch Backend API Server"

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    poppler-utils \
    libreoffice-nogui \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r deepsearch && \
    useradd -r -g deepsearch -m -d /home/deepsearch deepsearch && \
    mkdir -p /home/deepsearch/.paddlex /home/deepsearch/.paddleocr /data/files /data/backups /data/temp /app/logs && \
    chown -R deepsearch:deepsearch /app /data /home/deepsearch

# 切换到非 root 用户
USER deepsearch

# 环境变量
ENV HOME=/home/deepsearch \
    PADDLE_HOME=/home/deepsearch/.paddleocr \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

# 暴露端口
EXPOSE 8200

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8200/api/v1/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200", "--workers", "4"]
