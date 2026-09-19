"""假语音：终端里打一行字 = 识别出的一句话。看板上的“模拟说一句话”也走这里。
这也是现场太吵时的演示备份。"""
from __future__ import annotations
import asyncio
import sys
import time
from contracts import OnUtterance, Utterance


class FakeSpeech:
    def __init__(self, read_stdin: bool = True) -> None:
        self._on: OnUtterance | None = None
        self.read_stdin = read_stdin

    async def run(self, on_utterance: OnUtterance) -> None:
        self._on = on_utterance
        if not self.read_stdin or not sys.stdin or not sys.stdin.isatty():
            await asyncio.Event().wait()
        print("假语音已启动：输入一句话后回车。例：主持人，开始报价项目的会议")
        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                await asyncio.Event().wait()
            if line.strip():
                await self.inject(line.strip())

    async def inject(self, text: str) -> None:
        if self._on:
            await self._on(Utterance(text=text, ts=time.time()))

    async def say(self, text: str) -> None:
        print(f"  [机器人说] {text}")
        await asyncio.sleep(min(len(text) * 0.05, 2.0))
