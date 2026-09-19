"""Web 接口。D 负责页面（web/static/），接口形状改动要先和 A 说。
监听 0.0.0.0，同一局域网内的手机和大屏都能打开。
"""
from __future__ import annotations
import asyncio
import socket
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from brain import store
from brain.materials import MAX_CHARS, extract_text
from contracts import AgendaItem, Material, MeetingPrep, Utterance, to_dict

STATIC = Path(__file__).parent / "static"


class AgendaIn(BaseModel):
    title: str
    minutes: float


class PrepIn(BaseModel):
    project: str
    agenda: list[AgendaIn] = []
    participants: list[str] = []
    background: str = ""


class TextIn(BaseModel):
    text: str


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def build_app(orch) -> FastAPI:
    app = FastAPI(title="会议主持机器人")
    # 对方 H5 从自己的开发服务器直接 fetch 我们的 /api/* 时需要跨域放行；局域网演示，全部放开
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    @app.get("/")
    async def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/h5")
    async def h5():
        path = STATIC / "h5.html"
        return FileResponse(path) if path.exists() else JSONResponse({"error": "h5.html 还没做"}, 404)

    @app.get("/api/state")
    async def state():
        return orch.snapshot()

    # ---- 会前准备 ----
    @app.get("/api/preps")
    async def preps():
        return store.list_preps()

    @app.get("/api/prep/{project}")
    async def get_prep(project: str):
        p = store.load_prep(project)
        return to_dict(p) if p else JSONResponse({"error": "没有这个项目的准备"}, 404)

    @app.post("/api/prep")
    async def save_prep(body: PrepIn):
        old = store.load_prep(body.project)
        prep = MeetingPrep(project=body.project, agenda=[AgendaItem(a.title, a.minutes) for a in body.agenda],
                           participants=body.participants, background=body.background,
                           materials=old.materials if old and old.project == body.project else [])
        store.save_prep(prep)
        return {"ok": True}

    @app.post("/api/materials/{project}")
    async def upload(project: str, file: UploadFile = File(...)):
        prep = store.load_prep(project)
        if not prep or prep.project != project:
            return JSONResponse({"error": "先保存会议准备，再上传资料"}, 400)
        try:
            text = extract_text(file.filename, await file.read())
        except Exception as e:
            return JSONResponse({"error": str(e)}, 400)
        used = sum(len(m.text) for m in prep.materials)
        text = text[: max(MAX_CHARS - used, 0)]
        prep.materials = [m for m in prep.materials if m.filename != file.filename] + [Material(file.filename, text)]
        store.save_prep(prep)
        return {"ok": True, "filename": file.filename, "chars": len(text)}

    # ---- 会后 ----
    @app.get("/api/minutes/latest")
    async def minutes():
        return store.latest_minutes() or {}

    @app.get("/api/todos/{project}")
    async def todos(project: str):
        return [to_dict(t) for t in store.open_todos(project)]

    @app.post("/api/todos/{todo_id}/done")
    async def todo_done(todo_id: int):
        store.set_todo_status(todo_id, "done")
        return {"ok": True}

    # ---- 调试和演示备份：不靠麦克风和触摸也能驱动整条链路 ----
    @app.post("/api/debug/say")
    async def debug_say(body: TextIn):
        asyncio.create_task(orch.on_utterance(Utterance(text=body.text, ts=time.time())))
        return {"ok": True}

    @app.post("/api/debug/touch")
    async def debug_touch():
        asyncio.create_task(orch.on_touch("back_press"))
        return {"ok": True}

    # ---- 实时推送 ----
    @app.websocket("/ws")
    async def ws(sock: WebSocket):
        await sock.accept()
        unsubscribe = orch.bus.subscribe(sock.send_json)
        try:
            await sock.send_json(orch.snapshot())
            while True:
                await sock.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            unsubscribe()

    app.mount("/static", StaticFiles(directory=STATIC), name="static")
    return app
