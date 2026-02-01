# 多阶段构建 - 精简部署版
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 创建精简的 requirements (排除 whisper)
RUN grep -v "openai-whisper" requirements.txt > requirements-slim.txt \
    && pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements-slim.txt

# 生产镜像
FROM python:3.11-slim

WORKDIR /app

# 安装运行时依赖 (FFmpeg 用于基础音频处理)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 复制 wheels
COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*

# 复制应用代码
COPY src/ ./src/
COPY requirements.txt .
COPY .env.example .

# 创建必要目录
RUN mkdir -p output/skills output/content downloads data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
