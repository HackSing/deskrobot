"""WebRTC 全双工音频桥接。B 负责。

用途：机器人麦克风(open_pcm)关闭后立即调用扬声器(play_pcm)会让固件 DMA 碎片化，
`ctrl.audio.stream.begin` 持续 no_capacity/invalid_state，几十秒不自愈，只能断电
重启（已在真机上反复复现，参见 docs 交接记录）。WebRTC 全双工走设备独立的
``rtc.audio.full_duplex.v1`` 音频管线，与该问题无关，已用 SDK 自带的
sdk_media_lab 测试台验证：双向非静音、丢包为零、回声消除生效。因此语音输入
输出全部走这里，不再调用 ``robot.microphone``/``robot.audio.play_pcm``。

架构：这个模块起一个独立的小 FastAPI + uvicorn 服务（默认端口 8790），只做信令
中转和音频搬运，不含业务逻辑：

  浏览器桥接页（static/bridge.html，需要保持打开）
    - 用 app.rtc 的 offer/answer/candidate 协议建立一条常驻全双工会话
    - 下行：机器人麦克风音轨 -> AudioWorklet 转 16kHz PCM -> ws /ws/audio-in
    - 上行：ws /ws/audio-out 收到的 PCM -> 解码播放进发给机器人的音轨（默认静音）

  本模块（Python 侧）
    - /api/rtc/* 把浏览器的 offer/candidate 转发给 app.rtc.send_offer/send_candidate，
      /api/rtc/events 把 app.rtc.events() 转发给浏览器轮询
    - /ws/audio-in 收到的 PCM 喂 Segmenter 切句，每句起 ASR，识别出文本且包含机器人
      名字才回调 on_utterance（demo 方案要求"不做持续录音"，这里退而求其次做"持续
      监听但只在提到名字时才回调"，效果等价且不用做声学唤醒词）
    - /ws/audio-out 用来推 TTS PCM 给浏览器播放，await 浏览器回的完成确认
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from contracts import OnUtterance, Utterance
from speech import providers
from speech.segmenter import Segmenter

log = logging.getLogger("rtc_bridge")

STATIC_DIR = Path(__file__).resolve().parent / "static"
ROBOT_NAME = os.environ.get("ROBOT_NAME", "小登")
BRIDGE_PORT = int(os.environ.get("RTC_BRIDGE_PORT", "8790"))
AUDIO_OUT_ACK_TIMEOUT = 60.0


class RtcSignal(BaseModel):
    kind: str               # "offer" | "candidate"
    sdp: str | None = None
    candidate: str | None = None
    sdp_mid: str | None = None
    sdp_mline_index: int | None = None


class RtcClockPing(BaseModel):
    browser_send_us: int


class RtcFeedback(BaseModel):
    display_fps_x100: int
    frame_age_p95_us: int
    rtt_us: int
    audio_queue_ms: int
    audio_packet_loss_x100: int
    audio_jitter_us: int
    audio_concealed_frames: int
    congestion_level: int


class RtcBridge:
    """一个进程只开一条全双工会话；浏览器页面刷新会重新走一遍 /api/rtc/start。"""

    def __init__(self, app_ctx) -> None:
        self.app_ctx = app_ctx
        self.on_utterance: OnUtterance | None = None
        self.speaking = False
        self.hotwords: list[str] = []
        self._segmenter = Segmenter()
        self._audio_out_ws: WebSocket | None = None
        self._audio_out_ack = asyncio.Event()
        self.fastapi = self._build_app()

    def _build_app(self) -> FastAPI:
        web = FastAPI()

        @web.get("/")
        async def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "bridge.html")

        @web.post("/api/rtc/start")
        async def rtc_start() -> dict:
            try:
                session = await asyncio.to_thread(self.app_ctx.rtc.start, mode="audio")
                return {"ok": True, "session": session}
            except Exception as exc:  # noqa: BLE001 - 原样把设备拒绝原因带给页面
                log.error("rtc.start 失败: %s", exc)
                return JSONResponse({"ok": False, "error": str(exc)}, status_code=409)

        @web.post("/api/rtc/stop")
        async def rtc_stop() -> dict:
            try:
                stopped = await asyncio.to_thread(self.app_ctx.rtc.stop)
                return {"ok": True, "stopped": stopped}
            except Exception as exc:  # noqa: BLE001
                log.warning("rtc.stop 失败: %s", exc)
                return {"ok": False, "error": str(exc)}

        @web.post("/api/rtc/signal")
        async def rtc_signal(sig: RtcSignal) -> dict:
            if sig.kind == "offer":
                if not sig.sdp:
                    return JSONResponse({"ok": False, "error": "offer 缺少 sdp"}, status_code=400)
                await asyncio.to_thread(self.app_ctx.rtc.send_offer, sig.sdp)
            elif sig.kind == "candidate":
                if not sig.candidate or sig.sdp_mid is None or sig.sdp_mline_index is None:
                    return JSONResponse({"ok": False, "error": "candidate 参数不全"}, status_code=400)
                await asyncio.to_thread(
                    self.app_ctx.rtc.send_candidate,
                    sig.candidate,
                    sdp_mid=sig.sdp_mid,
                    sdp_mline_index=sig.sdp_mline_index,
                )
            else:
                return JSONResponse({"ok": False, "error": f"未知 kind: {sig.kind}"}, status_code=400)
            return {"ok": True}

        @web.get("/api/rtc/events")
        async def rtc_events(after: int = 0) -> dict:
            return {"events": self.app_ctx.rtc.events(after=after)}

        @web.post("/api/rtc/clock-ping")
        async def rtc_clock_ping(ping: RtcClockPing) -> dict:
            """设备期望的心跳；停发几秒后设备会把会话判定失效并断开（已实测复现）。"""
            try:
                await asyncio.to_thread(self.app_ctx.rtc.clock_ping, ping.browser_send_us)
            except Exception as exc:  # noqa: BLE001 - 掉一次心跳不致命，下次还会发
                log.warning("clock_ping 失败: %s", exc)
            return {"ok": True}

        @web.post("/api/rtc/feedback")
        async def rtc_feedback(fb: RtcFeedback) -> dict:
            try:
                await asyncio.to_thread(self.app_ctx.rtc.feedback, **fb.model_dump())
            except Exception as exc:  # noqa: BLE001
                log.warning("feedback 失败: %s", exc)
            return {"ok": True}

        @web.websocket("/ws/audio-in")
        async def audio_in(ws: WebSocket) -> None:
            await ws.accept()
            log.info("audio-in 浏览器已连接")
            try:
                while True:
                    frame = await ws.receive_bytes()
                    if self.speaking:            # 播报期间丢弃，避免识别到机器人自己的声音
                        continue
                    pcm = self._segmenter.feed(frame)
                    if pcm:
                        asyncio.create_task(self._recognize(pcm))
            except WebSocketDisconnect:
                log.info("audio-in 浏览器已断开")

        @web.websocket("/ws/audio-out")
        async def audio_out(ws: WebSocket) -> None:
            await ws.accept()
            self._audio_out_ws = ws
            log.info("audio-out 浏览器已连接")
            try:
                while True:
                    await ws.receive_json()      # 播放完成确认 {"done": true}
                    self._audio_out_ack.set()
            except WebSocketDisconnect:
                log.info("audio-out 浏览器已断开")
                if self._audio_out_ws is ws:
                    self._audio_out_ws = None

        return web

    async def _recognize(self, pcm: bytes) -> None:
        text = (await providers.asr(pcm, self.hotwords)).strip()
        if not text or ROBOT_NAME not in text:
            return
        if self.on_utterance:
            await self.on_utterance(Utterance(text=text, ts=time.time()))

    async def speak(self, pcm: bytes) -> None:
        """把 PCM 推给浏览器播放，等浏览器确认播完才返回。浏览器未连接时直接跳过。"""
        if self._audio_out_ws is None:
            log.warning("audio-out 浏览器未连接，跳过播报：%d 字节", len(pcm))
            return
        self._audio_out_ack.clear()
        await self._audio_out_ws.send_bytes(pcm)
        try:
            await asyncio.wait_for(self._audio_out_ack.wait(), AUDIO_OUT_ACK_TIMEOUT)
        except asyncio.TimeoutError:
            log.warning("等待浏览器播放确认超时（%.0fs）", AUDIO_OUT_ACK_TIMEOUT)

    async def serve(self) -> None:
        server = uvicorn.Server(
            uvicorn.Config(self.fastapi, host="0.0.0.0", port=BRIDGE_PORT, log_level="warning")
        )
        log.info(
            "RTC 音频桥接页：http://127.0.0.1:%d  （打开后点一下页面上的启动按钮，"
            "浏览器的自动播放策略要求先有一次点击才会真正播音频；保持标签页开着）",
            BRIDGE_PORT,
        )
        asyncio.get_event_loop().call_later(
            1.0, lambda: webbrowser.open(f"http://127.0.0.1:{BRIDGE_PORT}")
        )
        await server.serve()
