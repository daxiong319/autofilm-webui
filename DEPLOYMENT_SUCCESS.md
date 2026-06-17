# 🎉 AutoFilm WebUI 部署成功！

## 📍 访问地址

### WebUI 管理界面
**http://134.185.85.200:18096**

> ⚠️ 注意：外部访问端口为 **18096**（因为 8096 已被占用），容器内部端口保持 8096 不变

## 🐳 容器状态

| 容器名称 | 状态 | 端口映射 | 说明 |
|---------|------|---------|------|
| **autofilm-webui** | ✅ Running (healthy) | 18096:8096 | WebUI 管理面板 |
| **autofilm** | ✅ Running | 无（后台运行） | 核心任务引擎 |

## 📁 部署信息

- **部署路径**: `/home/autofilm-webui`
- **配置文件**: `/home/autofilm-webui/config/config.yaml`
- **日志目录**: `/home/autofilm-webui/logs`
- **媒体目录**: `/home/autofilm-webui/media`
- **代码仓库**: https://github.com/daxiong319/autofilm-webui

## 🚀 常用命令

### 查看容器状态
```bash
cd /home/autofilm-webui
docker compose ps
```

### 查看日志
```bash
# WebUI 日志
docker compose logs -f webui

# AutoFilm 核心日志
docker compose logs -f autofilm
```

### 重启服务
```bash
docker compose restart
```

### 停止服务
```bash
docker compose down
```

### 更新代码并重新部署
```bash
cd /home/autofilm-webui
git pull
docker compose up -d --build
```

## 🔧 配置说明

当前配置文件位于：`/home/autofilm-webui/config/config.yaml`

这是一个空配置，你需要根据实际情况添加：
- AList 服务器配置
- 媒体服务器配置（Emby/Jellyfin）
- 任务配置（Alist2Strm、Ani2Alist、LibraryPoster）

可以通过 WebUI 界面直接编辑配置，无需手动修改文件。

## 📊 功能模块

访问 http://134.185.85.200:18096 后，你可以使用以下功能：

1. **控制台** - 系统概览和统计信息
2. **AList 服务器** - 管理 AList 存储服务器
3. **媒体服务器** - 配置 Emby/Jellyfin 媒体服务器
4. **Alist2Strm 任务** - 生成 STRM 文件供媒体库扫描
5. **Ani2Alist 任务** - 动漫追番同步
6. **媒体库海报任务** - 自动生成媒体库海报
7. **日志中心** - 查看系统运行日志

## 🔐 安全建议

1. 如果服务器有公网 IP，建议配置防火墙只允许特定 IP 访问 18096 端口
2. 考虑在 WebUI 前添加反向代理（如 Nginx）并启用 HTTPS
3. 定期更新配置文件中的敏感信息（密码、API Key 等）

## 📝 下一步

1. 访问 http://134.185.85.200:18096
2. 在 WebUI 中配置 AList 服务器
3. 配置媒体服务器（Emby/Jellyfin）
4. 创建任务并测试手动运行
5. 设置 Cron 定时任务自动执行

---

**部署时间**: 2026-06-17 12:09  
**服务器**: 134.185.85.200  
**架构**: ARM64 (aarch64)  
**Docker Compose**: v2.35.1
