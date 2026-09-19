"""按音量做静音切句。输入 16 kHz 单声道 16 位 PCM 帧（SDK 每帧 60 ms），输出整句的 PCM。B 负责调参。"""
from __future__ import annotations
import array
import math


def rms(frame: bytes) -> float:
    samples = array.array("h", frame[: len(frame) // 2 * 2])
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


class Segmenter:
    def __init__(self, frame_ms: int = 60, threshold: float = 500.0, silence_ms: int = 700,
                 min_ms: int = 400, max_ms: int = 15000) -> None:
        self.frame_ms, self.threshold = frame_ms, threshold
        self.silence_frames = silence_ms // frame_ms
        self.min_frames, self.max_frames = min_ms // frame_ms, max_ms // frame_ms
        self._buf: list[bytes] = []
        self._voiced = 0
        self._quiet = 0

    def feed(self, frame: bytes) -> bytes | None:
        """喂一帧。句子结束时返回整句 PCM，否则返回 None。"""
        loud = rms(frame) >= self.threshold
        if not self._buf and not loud:
            return None
        self._buf.append(frame)
        if loud:
            self._voiced += 1
            self._quiet = 0
        else:
            self._quiet += 1
        if self._quiet >= self.silence_frames or len(self._buf) >= self.max_frames:
            pcm, voiced = b"".join(self._buf), self._voiced
            self._buf, self._voiced, self._quiet = [], 0, 0
            return pcm if voiced >= self.min_frames else None
        return None
