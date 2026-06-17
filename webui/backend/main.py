"""
AutoFilm WebUI 后端
基于 FastAPI，提供配置管理、任务触发、日志查看等接口
"""
import asyncio
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ──────────────────────────────────────────────
# 常量 & 全局状态
# ──────────────────────────────────────────────
CONFIG_PATH = Path(os.environ.get("AUTOFILM_CONFIG", "/config/config.yaml"))
LOG_DIR = Path(os.environ.get("AUTOFILM_LOG_DIR", "/logs"))
AUTOFILM_BIN = os.environ.get("AUTOFILM_BIN", "/app/autofilm")
# 静态文件目录：支持两种路径（本地开发和Docker部署）
_static_dir = Path(__file__).parent / "frontend" / "dist"
if not _static_dir.exists():
    _static_dir = Path(__file__).parent.parent / "frontend" / "dist"
STATIC_DIR = _static_dir

# 任务超时时间（秒），防止卡死的进程无限运行
TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "3600"))  # 默认 1 小时

app = FastAPI(title="AutoFilm WebUI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 正在运行的手动任务进程（task_id -> process）
_running_tasks: dict[str, subprocess.Popen] = {}
_running_lock = threading.Lock()
_task_logs: dict[str, list[str]] = {}  # 手动运行日志缓冲


# ──────────────────────────────────────────────
# Pydantic 数据模型（与 config.example.yaml 对应）
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
    kind: str = "emby"  # emby | jellyfin
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
# 配置读写工具函数
# ──────────────────────────────────────────────

def _read_raw_config() -> dict:
    """读取原始 YAML，文件不存在时返回空结构"""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _write_raw_config(data: dict) -> None:
    """将字典写回 YAML 文件"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _parse_config() -> FullConfig:
    raw = _read_raw_config()
    return FullConfig(
        alist=raw.get("alist", []),
        media_servers=raw.get("media_servers", []),
        alist2strm_tasks=raw.get("alist2strm_tasks", []),
        ani2alist_tasks=raw.get("ani2alist_tasks", []),
        library_poster_tasks=raw.get("library_poster_tasks", []),
    )


def _save_config(cfg: FullConfig) -> None:
    raw = cfg.model_dump(exclude_none=True)
    _write_raw_config(raw)


# ──────────────────────────────────────────────
# API 路由：全量配置
# ──────────────────────────────────────────────

@app.get("/api/config", response_model=FullConfig)
def get_config():
    return _parse_config()


@app.post("/api/config")
def save_config(cfg: FullConfig):
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：AList 服务器
# ──────────────────────────────────────────────

@app.get("/api/alist", response_model=list[AlistConfig])
def list_alist():
    return _parse_config().alist


@app.post("/api/alist")
def add_alist(item: AlistConfig):
    cfg = _parse_config()
    if any(a.id == item.id for a in cfg.alist):
        raise HTTPException(400, f"AList ID '{item.id}' 已存在")
    cfg.alist.append(item)
    _save_config(cfg)
    return {"ok": True}


@app.put("/api/alist/{alist_id}")
def update_alist(alist_id: str, item: AlistConfig):
    cfg = _parse_config()
    for i, a in enumerate(cfg.alist):
        if a.id == alist_id:
            cfg.alist[i] = item
            _save_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "AList 不存在")


@app.delete("/api/alist/{alist_id}")
def delete_alist(alist_id: str):
    cfg = _parse_config()
    cfg.alist = [a for a in cfg.alist if a.id != alist_id]
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：媒体服务器
# ──────────────────────────────────────────────

@app.get("/api/media_servers", response_model=list[MediaServerConfig])
def list_media_servers():
    return _parse_config().media_servers


@app.post("/api/media_servers")
def add_media_server(item: MediaServerConfig):
    cfg = _parse_config()
    if any(s.id == item.id for s in cfg.media_servers):
        raise HTTPException(400, f"媒体服务器 ID '{item.id}' 已存在")
    cfg.media_servers.append(item)
    _save_config(cfg)
    return {"ok": True}


@app.put("/api/media_servers/{server_id}")
def update_media_server(server_id: str, item: MediaServerConfig):
    cfg = _parse_config()
    for i, s in enumerate(cfg.media_servers):
        if s.id == server_id:
            cfg.media_servers[i] = item
            _save_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "媒体服务器不存在")


@app.delete("/api/media_servers/{server_id}")
def delete_media_server(server_id: str):
    cfg = _parse_config()
    cfg.media_servers = [s for s in cfg.media_servers if s.id != server_id]
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：Alist2Strm 任务
# ──────────────────────────────────────────────

@app.get("/api/tasks/alist2strm", response_model=list[Alist2StrmTask])
def list_alist2strm():
    return _parse_config().alist2strm_tasks


@app.post("/api/tasks/alist2strm")
def add_alist2strm(task: Alist2StrmTask):
    cfg = _parse_config()
    if any(t.id == task.id for t in cfg.alist2strm_tasks):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    cfg.alist2strm_tasks.append(task)
    _save_config(cfg)
    return {"ok": True}


@app.put("/api/tasks/alist2strm/{task_id}")
def update_alist2strm(task_id: str, task: Alist2StrmTask):
    cfg = _parse_config()
    for i, t in enumerate(cfg.alist2strm_tasks):
        if t.id == task_id:
            cfg.alist2strm_tasks[i] = task
            _save_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")


@app.delete("/api/tasks/alist2strm/{task_id}")
def delete_alist2strm(task_id: str):
    cfg = _parse_config()
    cfg.alist2strm_tasks = [t for t in cfg.alist2strm_tasks if t.id != task_id]
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：Ani2Alist 任务
# ──────────────────────────────────────────────

@app.get("/api/tasks/ani2alist", response_model=list[Ani2AlistTask])
def list_ani2alist():
    return _parse_config().ani2alist_tasks


@app.post("/api/tasks/ani2alist")
def add_ani2alist(task: Ani2AlistTask):
    cfg = _parse_config()
    if any(t.id == task.id for t in cfg.ani2alist_tasks):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    cfg.ani2alist_tasks.append(task)
    _save_config(cfg)
    return {"ok": True}


@app.put("/api/tasks/ani2alist/{task_id}")
def update_ani2alist(task_id: str, task: Ani2AlistTask):
    cfg = _parse_config()
    for i, t in enumerate(cfg.ani2alist_tasks):
        if t.id == task_id:
            cfg.ani2alist_tasks[i] = task
            _save_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")


@app.delete("/api/tasks/ani2alist/{task_id}")
def delete_ani2alist(task_id: str):
    cfg = _parse_config()
    cfg.ani2alist_tasks = [t for t in cfg.ani2alist_tasks if t.id != task_id]
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：LibraryPoster 任务
# ──────────────────────────────────────────────

@app.get("/api/tasks/library_poster", response_model=list[LibraryPosterTask])
def list_library_poster():
    return _parse_config().library_poster_tasks


@app.post("/api/tasks/library_poster")
def add_library_poster(task: LibraryPosterTask):
    cfg = _parse_config()
    if any(t.id == task.id for t in cfg.library_poster_tasks):
        raise HTTPException(400, f"任务 ID '{task.id}' 已存在")
    cfg.library_poster_tasks.append(task)
    _save_config(cfg)
    return {"ok": True}


@app.put("/api/tasks/library_poster/{task_id}")
def update_library_poster(task_id: str, task: LibraryPosterTask):
    cfg = _parse_config()
    for i, t in enumerate(cfg.library_poster_tasks):
        if t.id == task_id:
            cfg.library_poster_tasks[i] = task
            _save_config(cfg)
            return {"ok": True}
    raise HTTPException(404, "任务不存在")


@app.delete("/api/tasks/library_poster/{task_id}")
def delete_library_poster(task_id: str):
    cfg = _parse_config()
    cfg.library_poster_tasks = [t for t in cfg.library_poster_tasks if t.id != task_id]
    _save_config(cfg)
    return {"ok": True}


# ──────────────────────────────────────────────
# API 路由：手动触发任务
# ──────────────────────────────────────────────

@app.post("/api/run/{task_id}")
def run_task_now(task_id: str):
    """手动触发一次任务（单次运行，不依赖 cron）"""
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
                start_new_session=True,  # 创建新进程组，便于超时后清理
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
            pass  # 进程已关闭 stdout
        finally:
            proc.wait()

    def _watchdog():
        """监控进程，超时后强制终止"""
        try:
            proc.wait(timeout=TASK_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            import signal
            with _running_lock:
                _task_logs.setdefault(task_id, []).append(
                    f"[WARNING] 任务超时（{TASK_TIMEOUT_SECONDS}秒），正在强制终止..."
                )
            try:
                import os
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  # 发送 SIGTERM 到整个进程组
                proc.wait(timeout=5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                proc.kill()  # SIGTERM 失败，直接 SIGKILL
                proc.wait()
            with _running_lock:
                _task_logs.setdefault(task_id, []).append("[ERROR] 任务已因超时被强制终止")

    threading.Thread(target=_stream_logs, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    return {"ok": True, "message": f"任务 '{task_id}' 已启动"}


@app.get("/api/run/{task_id}/status")
def task_status(task_id: str):
    with _running_lock:
        proc = _running_tasks.get(task_id)
        if proc is None:
            return {"running": False, "exit_code": None}
        code = proc.poll()
        # 任务已结束，清理字典防止内存泄漏
        if code is not None:
            del _running_tasks[task_id]
        return {"running": code is None, "exit_code": code}


@app.get("/api/run/{task_id}/logs")
def task_run_logs(task_id: str):
    with _running_lock:
        logs = list(_task_logs.get(task_id, []))
    return {"logs": logs}


# ──────────────────────────────────────────────
# API 路由：日志文件
# ──────────────────────────────────────────────

@app.get("/api/logs")
def list_log_files():
    """列出日志目录下的所有日志文件"""
    if not LOG_DIR.exists():
        return {"files": []}
    files = sorted(
        [f.name for f in LOG_DIR.glob("*.log")],
        reverse=True,
    )
    return {"files": files}


@app.get("/api/logs/{filename}")
def get_log_file(filename: str, tail: int = 500):
    """获取日志文件末尾 N 行"""
    log_path = LOG_DIR / filename
    if not log_path.exists() or not log_path.is_file():
        raise HTTPException(404, "日志文件不存在")
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    return {"lines": [l.rstrip() for l in lines[-tail:]]}


@app.get("/api/logs/{filename}/stream")
async def stream_log(filename: str, request: Request):
    """SSE 实时推送最新日志"""
    log_path = LOG_DIR / filename
    if not log_path.exists():
        raise HTTPException(404, "日志文件不存在")

    async def event_gen():
        try:
            with open(log_path, encoding="utf-8", errors="replace") as f:
                f.seek(0, 2)  # 跳到文件末尾
                while True:
                    # 检查客户端是否已断开连接
                    if await request.is_disconnected():
                        break
                    line = f.readline()
                    if line:
                        yield f"data: {line.rstrip()}\n\n"
                    else:
                        await asyncio.sleep(0.5)
        except (ConnectionError, OSError):
            # 客户端断开连接时静默退出
            pass

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ──────────────────────────────────────────────
# API 路由：系统状态
# ──────────────────────────────────────────────

@app.get("/api/status")
def system_status():
    cfg = _parse_config()
    with _running_lock:
        running = [tid for tid, p in _running_tasks.items() if p.poll() is None]
    return {
        "alist_count": len(cfg.alist),
        "media_server_count": len(cfg.media_servers),
        "alist2strm_task_count": len(cfg.alist2strm_tasks),
        "ani2alist_task_count": len(cfg.ani2alist_tasks),
        "library_poster_task_count": len(cfg.library_poster_tasks),
        "total_tasks": len(cfg.alist2strm_tasks) + len(cfg.ani2alist_tasks) + len(cfg.library_poster_tasks),
        "running_tasks": running,
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ──────────────────────────────────────────────
# 静态文件服务（Vue 构建产物）
# ──────────────────────────────────────────────

if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


if __name__ == "__main__":
    port = int(os.environ.get("WEBUI_PORT", "8096"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
