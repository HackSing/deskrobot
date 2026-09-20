"""云端 ASR 和 TTS。B 负责：换成你选的供应方，改这个文件即可，签名不变。

ASR：火山引擎大模型语音识别极速版（HTTP 一次性接口，非流式）。新版语音控制台
只发一个 API Key，读 ASR_KEY 当作 ``X-Api-Key``；如果你用的是旧版控制台的
APP ID + Access Token 两件套，把 ASR_KEY 留空，改填 ASR_APP_ID/ASR_ACCESS_TOKEN。

TTS：edge-tts（免费、不需要 key），PyAV 解码重采样到机器人扬声器默认的
24000 Hz 单声道 16 位 PCM。ASR_URL/TTS_URL/TTS_KEY 当前用不到，保留是为了不改
契约签名——换供应方时按需要接上。
"""
from __future__ import annotations

import asyncio
import base64
import io
import os
import uuid

import httpx

ASR_URL, ASR_KEY = os.environ.get("ASR_URL", ""), os.environ.get("ASR_KEY", "")
ASR_APP_ID = os.environ.get("ASR_APP_ID", "")
ASR_ACCESS_TOKEN = os.environ.get("ASR_ACCESS_TOKEN", "")
TTS_URL, TTS_KEY = os.environ.get("TTS_URL", ""), os.environ.get("TTS_KEY", "")
TTS_VOICE = os.environ.get("TTS_VOICE", "zh-CN-XiaoxiaoNeural")

_VOLC_ASR_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
_VOLC_ASR_RESOURCE_ID = "volc.bigasr.auc_turbo"
_TTS_SAMPLE_RATE = 24000


def _pcm_to_wav(pcm: bytes, *, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sample_width)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


def _asr_auth_headers() -> dict[str, str]:
    if ASR_KEY:
        return {"X-Api-Key": ASR_KEY}
    return {"X-Api-App-Key": ASR_APP_ID, "X-Api-Access-Key": ASR_ACCESS_TOKEN}


async def asr(pcm_16k_mono_s16le: bytes, hotwords: list[str] | None = None) -> str:
    """一句话的 PCM（16kHz 单声道 16 位）-> 文本。识别不出或没配置 key 返回空字符串。"""
    if not ASR_KEY and not (ASR_APP_ID and ASR_ACCESS_TOKEN):
        return ""
    wav = _pcm_to_wav(pcm_16k_mono_s16le)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _VOLC_ASR_URL,
            headers={
                **_asr_auth_headers(),
                "X-Api-Resource-Id": _VOLC_ASR_RESOURCE_ID,
                "X-Api-Request-Id": str(uuid.uuid4()),
                "X-Api-Sequence": "-1",
            },
            json={
                "user": {"uid": "deskrobot"},
                "audio": {"data": base64.b64encode(wav).decode()},
                "request": {"model_name": "bigmodel", "enable_punc": True},
            },
            timeout=15.0,
        )
    if resp.headers.get("X-Api-Status-Code") != "20000000":
        return ""
    return resp.json().get("result", {}).get("text", "").strip()


def _decode_mp3_to_pcm(mp3: bytes, *, rate: int) -> bytes:
    import av

    chunks: list[bytes] = []
    with av.open(io.BytesIO(mp3)) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
        stream = container.streams.audio[0]
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(bytes(out.planes[0]))
        for out in resampler.resample(None):
            chunks.append(bytes(out.planes[0]))
    return b"".join(chunks)


async def tts(text: str) -> tuple[bytes, int]:
    """文本 -> (PCM 16 位单声道, 采样率)。机器人播放默认 24000 Hz，单次上限 4 MiB。"""
    import edge_tts

    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, TTS_VOICE)

    async def _collect() -> None:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])

    await asyncio.wait_for(_collect(), 45)
    mp3 = buf.getvalue()
    if not mp3:
        return b"", _TTS_SAMPLE_RATE
    pcm = await asyncio.to_thread(_decode_mp3_to_pcm, mp3, rate=_TTS_SAMPLE_RATE)
    return pcm, _TTS_SAMPLE_RATE
