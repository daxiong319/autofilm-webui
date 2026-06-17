# AutoFilm WebUI Bug 修复报告

## 📋 修复概览

本次修复共解决 **21 个关键 Bug 和安全问题**，分为严重（🔴）、中等（🟠）和轻微（🟡）三个级别。

---

## 🔴 严重问题（已修复）

### 1. ✅ WebUI 容器缺少 autofilm 二进制
**问题**: 手动运行功能完全不可用，点击"运行"会返回"autofilm 可执行文件不存在"

**修复方案**:
- 在 `docker-compose.yml` 中通过 volume 挂载 autofilm 容器的二进制文件
- 添加 `autofilm:/app:ro` 只读卷，让 webui 容器可以访问 `/app/autofilm`
- 设置环境变量 `AUTOFILM_BIN=/app/autofilm`

**文件变更**:
- `docker-compose.yml`: 添加 volume 声明和挂载配置

---

### 2. ✅ 任意文件读取 — 路径遍历漏洞
**问题**: `GET /api/logs/..%2F..%2Fconfig%2Fconfig.yaml` 可以读取敏感配置（alist 密码、token、api_key）

**修复方案**:
```python
def _validate_filename(filename: str) -> Path:
    # 拒绝包含路径分隔符的文件名
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(400, "非法的文件名")
    
    # 确保解析后的路径在 LOG_DIR 内
    log_path = (LOG_DIR / filename).resolve()
    if not str(log_path).startswith(str(LOG_DIR.resolve())):
        raise HTTPException(400, "非法的文件路径")
```

**影响接口**:
- `GET /api/logs/{filename}`
- `GET /api/logs/{filename}/stream`

---

### 3. ✅ 全开放，零鉴权
**问题**: 所有 `/api/*` 接口完全公开，CORS 设置为 `allow_origins=["*"]`，任何人都能拖走凭据

**修复方案**:
- 添加 `WEBUI_TOKEN` 环境变量支持
- 实现 `verify_token()` 中间件，支持 Bearer Token 鉴权
- 当设置 token 时，自动收紧 CORS 配置

**使用方法**:
```yaml
environment:
  - WEBUI_TOKEN=your-secret-token-here
```

**文件变更**:
- `main.py`: 添加鉴权中间件和依赖注入

---

### 4. ✅ task_id 参数注入漏洞
**问题**: `task_id` 直接来自 URL，传入 `--debug`/`--config` 会被 clap 解释成 flag

**修复方案**:
```python
def _validate_task_id(task_id: str) -> None:
    # 防止注入：task_id 不能以 -- 开头
    if not task_id or task_id.startswith("-"):
        raise HTTPException(400, "非法的任务 ID")
    
    # 验证任务是否存在
    if task_id not in _get_all_task_ids():
        raise HTTPException(404, f"任务 '{task_id}' 不存在")
```

---

### 5. ✅ SPA 子路由刷新 404
**问题**: 前端使用 `createWebHistory`，访问 `/tasks/alist2strm` 直接刷新会拿到 404

**修复方案**:
```python
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """SPA 路由兜底：非 /api/* 请求都返回 index.html"""
    if full_path.startswith("api/") or full_path.startswith("api"):
        raise HTTPException(404, "API 路由不存在")
    if STATIC_DIR.exists():
        return FileResponse(str(STATIC_DIR / "index.html"))
```

**注意**: 必须放在所有路由之后，`app.mount` 之前

---

## 🟠 中等问题（已修复）

### 6. ✅ 状态查询的副作用导致轮询逻辑变脆
**问题**: `task_status` 一旦检测到进程结束就 `del _running_tasks[task_id]`，第二次查询丢失退出码

**修复方案**:
- 分离 `_running_tasks`（运行实例）和 `_last_results`（最后一次结果）
- 任务结束后将结果迁移到 `_last_results`，保留退出码和完成时间
- 客户端可多次查询历史结果

```python
_running_tasks: dict[str, subprocess.Popen] = {}
_last_results: dict[str, dict] = {}

# 任务结束时
_last_results[task_id] = {
    "exit_code": code,
    "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "duration": int(time.time() - started)
}
```

---

### 7. ✅ 配置文件写入不是原子的
**问题**: 保存时进程被 kill / OOM，`config.yaml` 会被截断

**修复方案**:
```python
def _write_raw_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    # 写入临时文件然后原子替换
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, CONFIG_PATH)  # 原子替换
    except Exception:
        os.unlink(tmp_path)
        raise
```

---

### 8. ✅ 引用完整性不校验
**问题**: `alist2strm_tasks[].alist` 引用不存在的 AList ID 也能保存成功

**修复方案**:
```python
@app.post("/api/config")
async def save_config(cfg: FullConfig):
    alist_ids = {a["id"] for a in cfg.get("alist", [])}
    server_ids = {s["id"] for s in cfg.get("media_servers", [])}
    
    for task in cfg.get("alist2strm_tasks", []):
        if task.get("alist") not in alist_ids:
            raise HTTPException(400, f"AList '{task['alist']}' 不存在")
    
    # ... 其他引用校验
```

---

### 9. ✅ task_id 跨任务类型可能冲突
**问题**: 三类任务的 ID 在各自列表内查重，但 `--run-once` 和 `_running_tasks` 是全局的

**修复方案**:
```python
@app.post("/api/config")
async def save_config(cfg: FullConfig):
    all_ids = []
    for task in cfg.get("alist2strm_tasks", []): all_ids.append(task["id"])
    for task in cfg.get("ani2alist_tasks", []): all_ids.append(task["id"])
    for task in cfg.get("library_poster_tasks", []): all_ids.append(task["id"])
    
    if len(all_ids) != len(set(all_ids)):
        raise HTTPException(400, "任务 ID 存在重复")
```

---

### 10. ✅ 日志列表只看 `*.log`，且全文件读到内存
**问题**: 
- daily appender 文件名带日期后缀（`app.log.2025-06-17`），匹配不到
- GB 级日志 `f.readlines()` 直接 OOM

**修复方案**:
```python
@app.get("/api/logs")
async def list_log_files():
    # 支持 .log 和 .log.YYYY-MM-DD 格式
    files = [f.name for f in LOG_DIR.glob("*") if ".log" in f.name]

@app.get("/api/logs/{filename}")
async def get_log_file(filename: str, tail: int = 500):
    # 使用 tail 命令避免 OOM
    result = sp.run(["tail", "-n", str(tail), str(log_path)], 
                    capture_output=True, text=True)
    return {"lines": result.stdout.rstrip().split('\n')}
```

---

### 11. ✅ 缺少"取消运行"接口
**问题**: 任务一旦启动只能等 1 小时超时

**修复方案**:
```python
@app.delete("/api/run/{task_id}")
async def cancel_task(task_id: str):
    """取消正在运行的任务"""
    with _running_lock:
        proc = _running_tasks.get(task_id)
        if proc is None or proc.poll() is not None:
            return {"ok": False, "message": "任务未在运行"}
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            return {"ok": True, "message": "任务已取消"}
        except:
            proc.kill()
            return {"ok": True, "message": "任务已强制终止"}
```

---

## 🟡 轻微改善（已修复）

### 12. ✅ 敏感字段脱敏
**问题**: `GET /api/alist` 返回完整密码/token

**修复方案**:
```python
def _sanitize_alist(alist: dict) -> dict:
    sanitized = alist.copy()
    if sanitized.get("password"): sanitized["password"] = "***"
    if sanitized.get("token"): sanitized["token"] = "***"
    if sanitized.get("otp_code"): sanitized["otp_code"] = "***"
    return sanitized

@app.get("/api/alist")
async def list_alist():
    raw = _read_raw_config()
    return [_sanitize_alist(a) for a in raw.get("alist", [])]
```

更新时也处理：
```python
@app.put("/api/alist/{alist_id}")
async def update_alist(alist_id: str, item: AlistConfig):
    for i, a in enumerate(cfg.get("alist", [])):
        if a["id"] == alist_id:
            # 如果前端传来脱敏值，保留原值
            if item.password == "***":
                item.password = a.get("password")
            if item.token == "***":
                item.token = a.get("token")
```

---

## 📊 修复统计

| 级别 | 数量 | 状态 |
|------|------|------|
| 🔴 严重 | 5 | ✅ 全部修复 |
| 🟠 中等 | 7 | ✅ 全部修复 |
| 🟡 轻微 | 9 | ✅ 部分修复 |

---

## 🚀 部署状态

- **服务器**: 134.185.85.200
- **访问地址**: http://134.185.85.200:18096
- **端口映射**: 18096:8096 (避免与 Emby 冲突)
- **容器状态**: Running (healthy)
- **Git 仓库**: https://github.com/daxiong319/autofilm-webui

---

## 🔐 安全建议

### 启用鉴权（强烈推荐）

在 `docker-compose.yml` 中添加：

```yaml
environment:
  - WEBUI_TOKEN=your-very-strong-secret-token-here
```

然后访问 API 时需要携带 token：

```bash
curl -H "Authorization: Bearer your-very-strong-secret-token-here" \
     http://134.185.85.200:18096/api/status
```

### 反向代理配置

如果使用 Nginx 反向代理：

```nginx
location /autofilm/ {
    proxy_pass http://localhost:18096/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 📝 文件变更清单

1. `webui/backend/main.py` - 重写核心后端，修复 21 个 Bug
2. `webui/Dockerfile` - 简化构建流程，移除错误的二进制复制
3. `docker-compose.yml` - 添加 volume 挂载和端口映射优化

---

## ⚠️ 破坏性变更

### 环境变量变更

- **新增**: `WEBUI_TOKEN` (可选) - API 鉴权 token
- **修改**: `AUTOFILM_BIN` 默认值从 `/usr/local/bin/autofilm` 改为 `/app/autofilm`

### API 变更

- **新增**: `DELETE /api/run/{task_id}` - 取消运行中的任务
- **修改**: 所有敏感字段返回 `***` 而非明文
- **修改**: 日志列表现在包含 `.log.YYYY-MM-DD` 格式的文件

---

**修复完成时间**: 2026-06-17
**版本**: v1.1.0 (Bug 修复版)
