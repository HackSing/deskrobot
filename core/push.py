"""把会议快照主动推给 H5 那边的 HTTP 接口（对方自建页面，不走我们的 /ws）。

开关全在环境变量：
  H5_PUSH_URL      对方的接收地址。空字符串 = 关掉推送，什么都不做。
  H5_PUSH_TOKEN    非空时带 Authorization: Bearer <token>。
  H5_PUSH_TIMEOUT  单次请求超时，秒，默认 3。

载荷固定长这样：
  {"event": "<事件名>", "ts": 1726740000.123, "data": {<快照>}}

事件名一共五个，判断依据见 _event()：
  meeting_started  state 从非 meeting 变成 meeting
  meeting_ended    state 回到 idle，且 minutes 非空、和上一份不是同一份
  transcript       转写条数变了
  answer           last_answer 变了（question 或 text 不同）
  snapshot         其余任何变化（计时、cue、marks……）

送不到只记日志，绝不阻塞状态机。transcript 和 snapshot 会合并（只留最新一份），
meeting_started、answer、meeting_ended 三种一条都不会丢。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time

import httpx

log = logging.getLogger("core.push")

# 这三种事件必须逐条送到，不参与合并
IMPORTANT = ("meeting_started", "answer", "meeting_ended")


# ---------------------------------------------------------------------------
# 对方接口定了在这里改映射：改这一个函数就够，别的地方不用动。
# 现在原样把 Orchestrator.snapshot() 的字典透出去。
# ---------------------------------------------------------------------------
def adapt(snapshot: dict) -> dict:
    return snapshot


class H5Pusher:
    def __init__(self) -> None:
        self.url = os.environ.get("H5_PUSH_URL", "").strip()
        self.token = os.environ.get("H5_PUSH_TOKEN", "").strip()
        self.timeout = float(os.environ.get("H5_PUSH_TIMEOUT", "3"))
        self.http = httpx.AsyncClient(timeout=self.timeout)
        self.sent = 0
        self._prev: dict | None = None
        self._pending: list[dict] = []
        self._worker: asyncio.Task | None = None
        self._warned = False

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def subscribe(self, orch):
        """挂到状态机的广播上。返回退订函数。"""
        return orch.bus.subscribe(self.on_snapshot)

    async def on_snapshot(self, snapshot: dict) -> None:
        """状态机在 await 这个函数，所以它只算事件、排队，然后立刻返回。"""
        if not self.enabled:
            return
        try:
            event = _event(self._prev, snapshot)
            self._prev = snapshot
            self._enqueue({"event": event, "ts": time.time(), "data": adapt(snapshot)})
        except Exception as e:                     # 绝不把异常抛回状态机
            log.debug("H5 推送排队失败：%s", e)

    # ---------- 队列 ----------
    def _enqueue(self, payload: dict) -> None:
        if payload["event"] not in IMPORTANT:
            # 普通事件只保留最新一份待发，重要事件原样留在队列里
            self._pending = [p for p in self._pending if p["event"] in IMPORTANT]
        self._pending.append(payload)
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._drain())

    async def _drain(self) -> None:
        while self._pending:
            await self._post(self._pending.pop(0))

    async def _post(self, payload: dict) -> None:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            r = await self.http.post(self.url, json=payload, headers=headers)
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code} {r.text[:200]}")
            self.sent += 1
        except Exception as e:
            # 第一次说清楚，之后只留 debug，免得刷满终端
            if not self._warned:
                self._warned = True
                log.warning("H5 推送失败（%s）：%s", payload["event"], e)
            else:
                log.debug("H5 推送失败（%s）：%s", payload["event"], e)


def _event(prev: dict | None, now: dict) -> str:
    state = now.get("state")
    if state == "meeting" and (prev is None or prev.get("state") != "meeting"):
        return "meeting_started"
    if state == "idle" and now.get("minutes") and (prev or {}).get("minutes") != now.get("minutes"):
        return "meeting_ended"
    if len(now.get("transcript") or []) != len((prev or {}).get("transcript") or []):
        return "transcript"
    if _answer_key(now) != _answer_key(prev):
        return "answer"
    return "snapshot"


def _answer_key(snap: dict | None) -> tuple[str, str]:
    a = (snap or {}).get("last_answer") or {}
    return a.get("question", ""), a.get("text", "")
