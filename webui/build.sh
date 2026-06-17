#!/bin/bash
# AutoFilm WebUI 构建脚本
set -e

echo "========================================"
echo "  AutoFilm WebUI 构建脚本"
echo "========================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/webui/frontend"

echo ""
echo ">>> [1/3] 安装前端依赖..."
cd "$FRONTEND_DIR"
npm install

echo ""
echo ">>> [2/3] 构建前端..."
npm run build
echo "前端构建完成 → webui/frontend/dist/"

echo ""
echo ">>> [3/3] 构建 Docker 镜像..."
cd "$SCRIPT_DIR"
docker build -t autofilm-webui:latest ./webui

echo ""
echo "========================================"
echo "  构建完成！"
echo ""
echo "  启动服务："
echo "  docker-compose up -d"
echo ""
echo "  访问地址："
echo "  http://localhost:8096"
echo "========================================"
