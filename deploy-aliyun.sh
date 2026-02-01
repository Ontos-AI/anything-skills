#!/bin/bash
# Anything Skills 阿里云部署脚本
# 适用于 CentOS Stream 9

set -e

echo "=========================================="
echo "  Anything Skills 部署脚本"
echo "=========================================="

# 1. 安装 Docker
echo "[1/5] 检查并安装 Docker..."
if ! command -v docker &> /dev/null; then
    echo "正在安装 Docker..."
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl start docker
    systemctl enable docker
    echo "Docker 安装完成"
else
    echo "Docker 已安装"
fi

# 2. 安装 Docker Compose
echo "[2/5] 检查 Docker Compose..."
if ! docker compose version &> /dev/null; then
    echo "正在安装 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi
echo "Docker Compose 版本: $(docker compose version)"

# 3. 创建 .env 文件（如果不存在）
echo "[3/5] 配置环境变量..."
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env << 'EOF'
# LLM 配置 - 必填
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_MODEL=google/gemini-2.5-flash

# Whisper 配置
WHISPER_MODEL=base
WHISPER_LANGUAGE=zh
USE_LOCAL_TRANSCRIPTION=1

# 可选 API
ANTHROPIC_API_KEY=
YOUTUBE2TEXT_API_KEY=
BOCHA_API_KEY=
BOCHA_API_ENDPOINT=
BAILIAN_API_KEY=
BAILIAN_MCP_ENDPOINT=
BAILIAN_MCP_SERVICE_ID=
EOF
    echo "⚠️  请编辑 .env 文件，填入您的 API 密钥"
    echo "   运行: nano .env"
else
    echo ".env 文件已存在"
fi

# 4. 创建必要目录
echo "[4/5] 创建数据目录..."
mkdir -p output/skills output/content downloads data
chmod -R 777 output downloads data

# 5. 构建并启动
echo "[5/5] 构建并启动服务..."
docker compose build
docker compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 5

# 检查服务状态
if curl -s http://localhost:8000/ > /dev/null; then
    echo ""
    echo "=========================================="
    echo "  ✅ 部署成功！"
    echo "=========================================="
    echo ""
    echo "访问地址:"
    echo "  - 主页:     http://$(curl -s ifconfig.me):8000/"
    echo "  - Web UI:   http://$(curl -s ifconfig.me):8000/anything2skills"
    echo "  - API 文档: http://$(curl -s ifconfig.me):8000/docs"
    echo ""
    echo "常用命令:"
    echo "  查看日志:   docker compose logs -f"
    echo "  重启服务:   docker compose restart"
    echo "  停止服务:   docker compose down"
    echo ""
else
    echo "⚠️  服务可能未正常启动，请检查日志:"
    echo "   docker compose logs"
fi
