FROM python:3.12-slim

WORKDIR /webui

# Install Node.js for building frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Build frontend
COPY frontend/ ./frontend/
WORKDIR /webui/frontend
RUN npm install && npm run build

# Install Python dependencies
WORKDIR /webui
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ .

# Environment variables
ENV AUTOFILM_CONFIG=/config/config.yaml
ENV AUTOFILM_LOG_DIR=/logs
ENV AUTOFILM_BIN=/usr/local/bin/autofilm
ENV WEBUI_PORT=8096

EXPOSE 8096

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8096/api/status')"

CMD ["python", "main.py"]
