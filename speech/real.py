"""真语音链路：机器人 WebRTC 全双工音频 -> 切句 -> ASR -> 回调；TTS -> 全双工音轨。B 负责。

不用 ``robot.microphone``/``robot.audio.play_pcm``：真机反复验证过，麦克风关闭后
紧接着开扬声器流会让固件 DMA 碎片化，``ctrl.audio.stream.begin`` 持续
no_capacity/invalid_state，重试几十秒不自愈，只能断电重启机器人。WebRTC 全双工
（``rtc.audio.full_duplex.v1``）走独立的设备音频管线，不受这个问题影响，已用
SDK 自带的 sdk_media_lab 测试台验证可用。实际的信令中转、音频编解码和 ASR/TTS
调用都在 ``speech/rtc_bridge.py`` 里；这个文件只是薄薄一层，把 SpeechIO 契约接
到桥接模块上。
"""
from __future__ import annotations

from contracts import OnUtterance
from speech.rtc_bridge import RtcBridge


class RealSpeech:
    def __init__(self, app_ctx) -> None:      # app_ctx = ApplicationContext（要用到 .rtc）
        self.bridge = RtcBridge(app_ctx)
        self.hotwords: list[str] = []

    async def run(self, on_utterance: OnUtterance) -> None:
        self.bridge.on_utterance = on_utterance
        self.bridge.hotwords = self.hotwords
        await self.bridge.serve()

    async def say(self, text: str) -> None:
        from speech import providers

        self.bridge.speaking = True
        try:
            pcm, _rate = await providers.tts(text)
            if pcm:
                await self.bridge.speak(pcm)
        finally:
            self.bridge.speaking = False
