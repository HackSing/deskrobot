"""云端 ASR 和 TTS。B 负责：换成你选的供应方，改 URL 和 key。

参考实现：SDK 仓库 examples/first_meeting/meeting/cloud.py（火山 STT/TTS）
免 key 的 TTS 备选：examples/dshtts_speaker（edge-tts）
"""
from __future__ import annotations
import os

ASR_URL, ASR_KEY = os.environ.get("ASR_URL", ""), os.environ.get("ASR_KEY", "")
TTS_URL, TTS_KEY = os.environ.get("TTS_URL", ""), os.environ.get("TTS_KEY", "")


async def asr(pcm_16k_mono_s16le: bytes, hotwords: list[str] | None = None) -> str:
    """一句话的 PCM -> 文本。识别不出返回空字符串。"""
    raise NotImplementedError("B：接入 ASR 供应方")


async def tts(text: str) -> tuple[bytes, int]:
    """文本 -> (PCM 16 位单声道, 采样率)。机器人播放默认 24000 Hz，单次上限 4 MiB。"""
    raise NotImplementedError("B：接入 TTS 供应方")
