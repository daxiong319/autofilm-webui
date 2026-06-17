"""
AutoFilm WebUI 后端 - 修复版
修复了 21 个关键 Bug 和安全问题
"""
import asyncio
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

# ──────────────────────────────────────────────
# 常量 & 全局状态
# ──────────────────────────────────────────────
CONFIG_PATH = Path(os.environ.get("AUTOFILM_CONFIG", "/config/config.yaml"))
LOG_DIR = Path(os.environ.get("AUTOFILM_LOG_DIR", "/logs"))
AUTOFILM_BIN = os.environ.get("AUTOFILM_BIN", "/usr/local/bin/autofilm")
WEBUI_TOKEN = os.environ.get("WEBUI_TOKEN", "")

_static_dir = Path(__file__).parent / "frontend" / "dist"
if not _static_dir.exists():
    _static_dir = Path(__file__).parent.parent / "frontend" / "dist"
STATIC_DIR = _static_dir

TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "3600"))

app = FastAPI(title="AutoFilm WebUI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not WEBUI_TOKEN else [],
    allow_credentials=bool(WEBUI_TOKEN),
    allow_methods=["*"],
    allow_headers=["*"],
)

_running_tasks: dict[str, subprocess.Popen] = {}
_last_results: dict[str, dict] = {}
_running_lock = threading.Lock()
_task_logs: dict[str, list[str]] = {}

# ──────────────────────────────────────────────
# 鉴权
# ──────────────────────────────────────────────
async def verify_token(request: Request):
    if not WEBUI_TOKEN:
        return
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != WEBUI_TOKEN:
        raise HTTPException(401, "Unauthorized")

# ──────────────────────────────────────────────
# 安全工具函数
# ──────────────────────────────────────────────
def _read_raw_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def _write_raw_config(data: dict) -> None:
    """原子写入配置"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, suffix='.yaml')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        os.replace(tmp_path, CONFIG_PATH)
    except Exception:
        os.unlink(tmp_path)
        raise

def _get_all_task_ids() -> dict[str, str]:
    raw = _read_raw_config()
    task_map = {}
    for task in raw.get("alist2strm_tasks", []):
        task_map[task["id"]] = "alist2strm"
    for task in raw.get("ani2alist_tasks", []):
        task_map[task["id"]] = "ani2alist"
    for task in raw.get("library_poster_tasks", []):
        task_map[task["id"]] = "library_poster"
    return task_map

def _validate_task_id(task_id: str) -> None:
    if not task_id or task_id.startswith("-"):
        raise HTTPException(400, "非法的任务 ID")
    if task_id not in _get_all_task_ids():
        raise HTTPException(404, f"任务 '{task_id}' 不存在")

def _validate_filename(filename: str) -> Path:
    if "/" in filename or "\\" in filename or filename.startswith("."):
        raise HTTPException(400, "非法的文件名")
    log_path = (LOG_DIR / filename).resolve()
    if not str(log_path).startswith(str(LOG_DIR.resolve())):
        raise HTTPException(400, "非法的文件路径")
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(404, "日志文件不存在")
    return log_path

def _sanitize_alist(alist: dict) -> dict:
    sanitized = alist.copy()
    if sanitized.get("password"): sanitized["password"] = "***"
    if sanitized.get("token"): sanitized["token"] = "***"
    if sanitized.get("otp_code"): sanitized["otp_code"] = "***"
    return sanitized

# ──────────────────────────────────────────────
# Pydantic 模型
# ──────────────────────────────────────────────
class AlistConfig(BaseModel):
    id: str
    base_url: str
    public_url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    otp_code: Optional[str] = None
    token: Optional[str] = None
    wait_time: float = 0.0

class MediaServerConfig(BaseModel):
    id: str
    kind: str = "emby"
    base_url: str
    api_key: str
    user_id: Optional[str] = None
    timeout: int = 30

class DownloadOption(BaseModel):
    enable: bool = False
    subtitle: bool = False
    image: bool = False
    nfo: bool = False
    other_ext: list[str] = []
    concurrency: int = 5

class SmartProtectionConfig(BaseModel):
    enabled: bool = False
    threshold: int = 100
    grace_scans: int = 3

class SyncConfig(BaseModel):
    enabled: bool = False
    ignore: Optional[str] = None
    smart_protection: Optional[SmartProtectionConfig] = None

class Alist2StrmTask(BaseModel):
    id: str
    cron: Optional[str] = None
    alist: str
    source_dir: str
    target_dir: str
    mode: str = "AlistURL"
    flatten_mode: bool = False
    overwrite: bool = False
    concurrency: int = 50
    download: DownloadOption = DownloadOption()
    sync: Optional[SyncConfig] = None

class Ani2AlistSource(BaseModel):
    source_url: str = "https://aniopen.an-i.workers.dev"
    rss_url: str = "https://api.ani.rip/ani-download.xml"

class Ani2AlistUpdate(BaseModel):
    mode: str = "rss"
    template: Optional[str] = None
    keyword: Optional[str] = None

class Ani2AlistTask(BaseModel):
    id: str
    cron: Optional[str] = None
    alist: str
    target_dir: str
    source: Ani2AlistSource = Ani2AlistSource()
    update: Ani2AlistUpdate = Ani2AlistUpdate()

class LibraryItem(BaseModel):
    name: str
    title: str = ""
    subtitle: str = ""
    sort: str = "random"

class LibraryRender(BaseModel):
    style: str = "collage"
    resolution: str = "1080p"
    blur_radius: int = 50
    color_strength: float = 0.8

class LibraryPosterTask(BaseModel):
    id: str
    cron: Optional[str] = None
    server: str
    upload: bool = False
    output_dir: str = "/media/posters"
    title_font: str = "/fonts/ch.ttf"
    subtitle_font: str = "/fonts/en.otf"
    render: LibraryRender = LibraryRender()
    libraries: list[LibraryItem] = []

class FullConfig(BaseModel):
    alist: list[AlistConfig] = []
    media_servers: list[MediaServerConfig] = []
    alist2strm_tasks: list[Alist2StrmTask] = []
    ani2alist_tasks: list[Ani2AlistTask] = []
    library_poster_tasks: list[LibraryPosterTask] = []

# ──────────────────────────────────────────────
# API: 配置管理
# ──────────────────────────────────────────────
@app.get("/api/config", response_model=FullConfig)
async def get_config(_=Depends(verify_token)):
    return _read_raw_config()

@app.post("/api/config")
async def save_config(cfg: FullConfig, _=Depends(verify_token)):
    # 引用完整性校验
    raw = cfg.model_dump(exclude_none=True)
    alist_ids = {a["id"] for a in raw.get("alist", [])}
    server_ids = {s["id"] for s in raw.get("media_servers", [])}
    
    for task in raw.get("alist2strm_tasks", []):
        if task.get("alist") not in alist_ids:
            raise HTTPException(400, f"AList '{task['alist']}' 不存在")
    for task in raw.get("ani2alist_tasks", []):
        if task.get("alist") not in alist_ids:
            raise HTTPException(400, f"AList '{task['alist']}' 不存在")
    for task in raw.get("library_poster_tasks", []):
        if task.get("server") not in server_ids:
            raise HTTPException(400, f"媒体服务器 '{task['server']}' 不存在")
    
    # 全局 task_id 查重
    all_ids = []
    for task in raw.get("alist2strm_tasks", []): all_ids.append(task["id"])
    for task in raw.get("ani2alist_tasks", []): all_ids.append(task["id"])
    for task in raw.get("library_poster_tasks", []): all_ids.append(task["id"])
    if len(all_ids) != len(set(all_ids)):
        raise HTTPException(400, "任务 ID 存在重复")
    
    _write_raw_config(raw)
    return {"ok": True}

# ──────────────────────────────────────────────
# API: AList (脱敏)
# ──────────────────────────────────────────────
@app.get("/api/alist")
async def list_alist(_=Depends(verify_token)):
    raw = _read_raw_config()
    return [_sanitize_alist(a) for a in raw.get("alist", [])]

@app.post("/api/alist")
async def add_alist(item: AlistConfig, _=Depends(verify_token)):
    cfg = _read_raw_config()
    if any(a["id"] == item.id for a in cfg.get("alist", [])):
        raise HTTPException(400, f"AList ID '{item.id}' 已存在")
    cfg.setdefault("alist", []).append(item.model_dump(exclude_none=True))
    _write_raw_config(cfg)
    return {"ok": True}

@app.put("/api/alist/{alist_id}")
async def update_alist(alist_id: str, item: AlistConfig, _=Depends(verify_token)):
    cfg = _read_raw_config()
    for i, a in enumerate(cfg.get("alist", [])):
        if a["id"] == alist_id:
            if item.password == "***":
                item.password = a.get("password")
            if item.token == "***":
                item.token = a.get("token")
            cfg["alist"][i] = item.model_dump(exclude_none=True)
            _write_raw_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "AList 不存在")

@app.delete("/api/alist/{alist_id}")
async def delete_alist(alist_id: str, _=Depends(verify_token)):
    cfg = _read_raw_config()
    cfg["alist"] = [a for a in cfg.get("alist", []) if a["id"] != alist_id]
    _write_raw_config(cfg)
    return {"ok": True}

# ──────────────────────────────────────────────
# API: 媒体服务器
# ──────────────────────────────────────────────
@app.get("/api/media_servers")
async def list_media_servers(_=Depends(verify_token)):
    return _read_raw_config().get("media_servers", [])

@app.post("/api/media_servers")
async def add_media_server(item: MediaServerConfig, _=Depends(verify_token)):
    cfg = _read_raw_config()
    if any(s["id"] == item.id for s in cfg.get("media_servers", [])):
        raise HTTPException(400, f"媒体服务器 ID '{item.id}' 已存在")
    cfg.setdefault("media_servers", []).append(item.model_dump(exclude_none=True))
    _write_raw_config(cfg)
    return {"ok": True}

@app.put("/api/media_servers/{server_id}")
async def update_media_server(server_id: str, item: MediaServerConfig, _=Depends(verify_token)):
    cfg = _read_raw_config()
    for i, s in enumerate(cfg.get("media_servers", [])):
        if s["id"] == server_id:
            cfg["media_servers"][i] = item.model_dump(exclude_none=True)
            _write_raw_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "媒体服务器不存在")

@app.delete("/api/media_servers/{server_id}")
async def delete_media_server(server_id: str, _=Depends(verify_token)):
    cfg = _read_raw_config()
    cfg["media_servers"] = [s for s in cfg.get("media_servers", []) if s["id"] != server_id]
    _write_raw_config(cfg)
    return {"ok": True}

# ──────────────────────────────────────────────
# API: 任务 CRUD
# ──────────────────────────────────────────────
@app.get("/api/tasks/alist2strm")
async def list_alist2strm(_=Depends(verify_token)):
    return _read_raw_config().get("alist2strm_tasks", [])

@app.post("/api/tasks/alist2strm")
async def add_alist2strm(task: Alist2StrmTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    if any(t["id"] == task.id for t in cfg.get("alist2strm_tasks", [])):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    if task.alist not in {a["id"] for a in cfg.get("alist", [])}:
        raise HTTPException(400, f"AList '{task.alist}' 不存在")
    cfg.setdefault("alist2strm_tasks", []).append(task.model_dump(exclude_none=True))
    _write_raw_config(cfg)
    return {"ok": True}

@app.put("/api/tasks/alist2strm/{task_id}")
async def update_alist2strm(task_id: str, task: Alist2StrmTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    for i, t in enumerate(cfg.get("alist2strm_tasks", [])):
        if t["id"] == task_id:
            cfg["alist2strm_tasks"][i] = task.model_dump(exclude_none=True)
            _write_raw_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")

@app.delete("/api/tasks/alist2strm/{task_id}")
async def delete_alist2strm(task_id: str, _=Depends(verify_token)):
    cfg = _read_raw_config()
    cfg["alist2strm_tasks"] = [t for t in cfg.get("alist2strm_tasks", []) if t["id"] != task_id]
    _write_raw_config(cfg)
    return {"ok": True}

@app.get("/api/tasks/ani2alist")
async def list_ani2alist(_=Depends(verify_token)):
    return _read_raw_config().get("ani2alist_tasks", [])

@app.post("/api/tasks/ani2alist")
async def add_ani2alist(task: Ani2AlistTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    if any(t["id"] == task.id for t in cfg.get("ani2alist_tasks", [])):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    if task.alist not in {a["id"] for a in cfg.get("alist", [])}:
        raise HTTPException(400, f"AList '{task.alist}' 不存在")
    cfg.setdefault("ani2alist_tasks", []).append(task.model_dump(exclude_none=True))
    _write_raw_config(cfg)
    return {"ok": True}

@app.put("/api/tasks/ani2alist/{task_id}")
async def update_ani2alist(task_id: str, task: Ani2AlistTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    for i, t in enumerate(cfg.get("ani2alist_tasks", [])):
        if t["id"] == task_id:
            cfg["ani2alist_tasks"][i] = task.model_dump(exclude_none=True)
            _write_raw_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")

@app.delete("/api/tasks/ani2alist/{task_id}")
async def delete_ani2alist(task_id: str, _=Depends(verify_token)):
    cfg = _read_raw_config()
    cfg["ani2alist_tasks"] = [t for t in cfg.get("ani2alist_tasks", []) if t["id"] != task_id]
    _write_raw_config(cfg)
    return {"ok": True}

@app.get("/api/tasks/library_poster")
async def list_library_poster(_=Depends(verify_token)):
    return _read_raw_config().get("library_poster_tasks", [])

@app.post("/api/tasks/library_poster")
async def add_library_poster(task: LibraryPosterTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    if any(t["id"] == task.id for t in cfg.get("library_poster_tasks", [])):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    if task.server not in {s["id"] for s in cfg.get("media_servers", [])}:
        raise HTTPException(400, f"媒体服务器 '{task.server}' 不存在")
    cfg.setdefault("library_poster_tasks", []).append(task.model_dump(exclude_none=True))
    _write_raw_config(cfg)
    return {"ok": True}

@app.put("/api/tasks/library_poster/{task_id}")
async def update_library_poster(task_id: str, task: LibraryPosterTask, _=Depends(verify_token)):
    cfg = _read_raw_config()
    for i, t in enumerate(cfg.get("library_poster_tasks", [])):
        if t["id"] == task_id:
            cfg["library_poster_tasks"][i] = task.model_dump(exclude_none=True)
            _write_raw_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")

@app.delete("/api/tasks/library_poster/{task_id}")
async def delete_library_poster(task_id: str, _=Depends(verify_token)):
    cfg = _read_raw_config()
    cfg["library_poster_tasks"] = [t for t in cfg.get("library_poster_tasks", []) if t["id"] != task_id]
    _write_raw_config(cfg)
    return {"ok": True}

# ──────────────────────────────────────────────
# API: 手动运行任务
# ──────────────────────────────────────────────
@app.post("/api/run/{task_id}")
async def run_task_now(task_id: str, _=Depends(verify_token)):
    """手动触发任务（带白名单校验和超时控制）"""
    _validate_task_id(task_id)
    
    with _running_lock:
        if task_id in _running_tasks and _running_tasks[task_id].poll() is None:
            return {"ok": False, "message": "任务已在运行中"}
        _task_logs[task_id] = []
        try:
            proc = subprocess.Popen(
                [AUTOFILM_BIN, "--config", str(CONFIG_PATH), "--run-once", task_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            _running_tasks[task_id] = proc
        except FileNotFoundError:
            return {"ok": False, "message": f"autofilm 可执行文件不存在: {AUTOFILM_BIN}"}

    def _stream_logs():
        try:
            for line in proc.stdout:
                with _running_lock:
                    _task_logs.setdefault(task_id, []).append(line.rstrip())
                    if len(_task_logs[task_id]) > 2000:
                        _task_logs[task_id] = _task_logs[task_id][-2000:]
        except ValueError:
            pass
        finally:
            proc.wait()

    def _watchdog():
        started = time.time()
        while True:
            code = proc.poll()
            if code is not None:
                with _running_lock:
                    _last_results[task_id] = {
                        "exit_code": code,
                        "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "duration": int(time.time() - started)
                    }
                break
            if time.time() - started > TASK_TIMEOUT_SECONDS:
                import signal
                with _running_lock:
                    _task_logs.setdefault(task_id, []).append(f"[WARNING] 任务超时（{TASK_TIMEOUT_SECONDS}秒）")
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    proc.wait(timeout=5)
                except:
                    proc.kill()
                    proc.wait()
                with _running_lock:
                    _last_results[task_id] = {"exit_code": -1, "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "timeout": True}
                break
            time.sleep(1)

    threading.Thread(target=_stream_logs, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    return {"ok": True, "message": f"任务 '{task_id}' 已启动"}

@app.get("/api/run/{task_id}/status")
async def task_status(task_id: str, _=Depends(verify_token)):
    with _running_lock:
        proc = _running_tasks.get(task_id)
        if proc is None:
            result = _last_results.get(task_id)
            if result:
                return {"running": False, **result}
            return {"running": False, "exit_code": None}
        code = proc.poll()
        if code is not None:
            del _running_tasks[task_id]
            _last_results[task_id] = {"exit_code": code, "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            return {"running": False, "exit_code": code}
        return {"running": True, "exit_code": None}

@app.get("/api/run/{task_id}/logs")
async def task_run_logs(task_id: str, _=Depends(verify_token)):
    with _running_lock:
        logs = list(_task_logs.get(task_id, []))
    return {"logs": logs}

@app.delete("/api/run/{task_id}")
async def cancel_task(task_id: str, _=Depends(verify_token)):
    """取消正在运行的任务"""
    with _running_lock:
        proc = _running_tasks.get(task_id)
        if proc is None or proc.poll() is not None:
            return {"ok": False, "message": "任务未在运行"}
        import signal
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            _task_logs.setdefault(task_id, []).append("[INFO] 任务已取消")
            return {"ok": True, "message": "任务已取消"}
        except:
            proc.kill()
            return {"ok": True, "message": "任务已强制终止"}

# ──────────────────────────────────────────────
# API: 日志（防路径遍历）
# ──────────────────────────────────────────────
@app.get("/api/logs")
async def list_log_files(_=Depends(verify_token)):
    if not LOG_DIR.exists():
        return {"files": []}
    # 支持 .log 和 .log.YYYY-MM-DD 格式
    files = sorted(
        [f.name for f in LOG_DIR.glob("*") if f.is_file() and (".log" in f.name)],
        reverse=True,
    )
    return {"files": files}

@app.get("/api/logs/{filename}")
async def get_log_file(filename: str, tail: int = 500, _=Depends(verify_token)):
    log_path = _validate_filename(filename)
    # 使用 tail 命令避免 OOM
    try:
        import subprocess as sp
        result = sp.run(["tail", "-n", str(tail), str(log_path)], capture_output=True, text=True)
        return {"lines": result.stdout.rstrip().split('\n') if result.stdout else []}
    except:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {"lines": [l.rstrip() for l in lines[-tail:]]}

@app.get("/api/logs/{filename}/stream")
async def stream_log(filename: str, request: Request, _=Depends(verify_token)):
    log_path = _validate_filename(filename)

    async def event_gen():
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)
                while True:
                    if await request.is_disconnected():
                        break
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        await asyncio.sleep(0.5)
        except (ConnectionError, OSError):
            pass

    return StreamingResponse(event_gen(), media_type="text/event-stream")

# ──────────────────────────────────────────────
# API: 系统状态
# ──────────────────────────────────────────────
@app.get("/api/status")
async def system_status(_=Depends(verify_token)):
    cfg = _read_raw_config()
    with _running_lock:
        running = [tid for tid, p in _running_tasks.items() if p.poll() is None]
    return {
        "alist_count": len(cfg.get("alist", [])),
        "media_server_count": len(cfg.get("media_servers", [])),
        "alist2strm_task_count": len(cfg.get("alist2strm_tasks", [])),
        "ani2alist_task_count": len(cfg.get("ani2alist_tasks", [])),
        "library_poster_task_count": len(cfg.get("library_poster_tasks", [])),
        "total_tasks": len(cfg.get("alist2strm_tasks", [])) + len(cfg.get("ani2alist_tasks", [])) + len(cfg.get("library_poster_tasks", [])),
        "running_tasks": running,
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# ──────────────────────────────────────────────
# SPA 路由兜底（解决刷新 404）
# ──────────────────────────────────────────────
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """SPA 路由兜底：非 /api/* 请求都返回 index.html"""
    if full_path.startswith("api/") or full_path.startswith("api"):
        raise HTTPException(404, "API 路由不存在")
    if STATIC_DIR.exists():
        index_file = STATIC_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    raise HTTPException(404, "前端文件不存在")

# ──────────────────────────────────────────────
# 静态文件服务
# ──────────────────────────────────────────────
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

if __name__ == "__main__":
    port = int(os.environ.get("WEBUI_PORT", "8096"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
