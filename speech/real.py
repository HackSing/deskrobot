"""真语音链路：机器人麦克风 -> 切句 -> ASR -> 回调；TTS -> 机器人扬声器。B 负责。"""
from __future__ import annotations
import asyncio
import time

from contracts import OnUtterance, Utterance
from speech import providers
from speech.segmenter import Segmenter


class RealSpeech:
    def __init__(self, robot) -> None:            # robot = ApplicationContext.robot
        self.robot = robot
        self._speaking = False
        self.hotwords: list[str] = []

    async def run(self, on_utterance: OnUtterance) -> None:
        seg = Segmenter()
        mic = await asyncio.to_thread(self.robot.microphone.open_pcm)
        try:
            while True:
                try:
                    frame = await asyncio.to_thread(mic.read, 1.0)
                except TimeoutError:                                # SDK：1 秒内没有帧
                    continue
                if self._speaking:                                  # 播报期间丢弃，避免听到自己
                    continue
                pcm = seg.feed(frame.data)
                if pcm:
                    asyncio.create_task(self._recognize(pcm, on_utterance))
        finally:
            await asyncio.to_thread(mic.close)

    async def _recognize(self, pcm: bytes, on_utterance: OnUtterance) -> None:
        text = (await providers.asr(pcm, self.hotwords)).strip()
        if text:
            await on_utterance(Utterance(text=text, ts=time.time()))

    async def say(self, text: str) -> None:
        self._speaking = True
        try:
            pcm, rate = await providers.tts(text)
            playback = await asyncio.to_thread(self.robot.audio.play_pcm, pcm, sample_rate_hz=rate)
            await asyncio.to_thread(playback.wait, 60.0)            # AudioPlayback 是 Job，wait 到播完
            await asyncio.sleep(0.3)                                # 留一点尾巴，避免录到回声
        finally:
            self._speaking = False
