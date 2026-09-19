"""看板用的广播：状态一变就通知所有订阅者（web 的 WebSocket）。"""
from __future__ import annotations
import asyncio
from typing import Awaitable, Callable

Listener = Callable[[dict], Awaitable[None]]


class Broadcaster:
    def __init__(self) -> None:
        self._listeners: set[Listener] = set()

    def subscribe(self, fn: Listener) -> Callable[[], None]:
        self._listeners.add(fn)
        return lambda: self._listeners.discard(fn)

    async def publish(self, snapshot: dict) -> None:
        for fn in list(self._listeners):
            try:
                await fn(snapshot)
            except Exception:
                self._listeners.discard(fn)
