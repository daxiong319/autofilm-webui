FROM python:3.12-slim

WORKDIR /webui

# 安装依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ .

# 复制前端构建产物（提前 npm run build）
COPY frontend/dist/ /webui/frontend/dist/

# 环境变量默认值
ENV AUTOFILM_CONFIG=/config/config.yaml
ENV AUTOFILM_LOG_DIR=/logs
ENV AUTOFILM_BIN=/app/autofilm
ENV WEBUI_PORT=8096

EXPOSE 8096

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8096/api/status')"

CMD ["python", "main.py"]
