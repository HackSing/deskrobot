"""假机器人：把反馈打印出来。按回车当作拍背（只在没有假语音占用终端时有用；看板上也有“拍背”按钮）。"""
from __future__ import annotations
import asyncio
from contracts import OnTouch
from robot_io.cues import CUE_TABLE, progress_color


class FakeRobot:
    def __init__(self) -> None:
        self._on_touch: OnTouch | None = None
        self._bottom = None
        self.last_cue = "standby"

    async def cue(self, name: str) -> None:
        self.last_cue = name
        spec = CUE_TABLE.get(name, {})
        print(f"  [机器人] {name}: 表情={spec.get('behavior')} 侧灯={spec.get('side')}")

    async def set_progress(self, ratio: float) -> None:
        state = "off" if ratio < 0 else progress_color(ratio)
        if state != self._bottom:
            self._bottom = state
            print(f"  [机器人] 底灯 -> {state}")

    async def run_inputs(self, on_touch: OnTouch) -> None:
        self._on_touch = on_touch
        await asyncio.Event().wait()

    async def touch(self, kind: str = "back_press") -> None:     # 给 web 的调试按钮用
        if self._on_touch:
            await self._on_touch(kind)

    async def face_tracking(self, on: bool) -> None:
        print(f"  [机器人] 人脸跟随 {'开' if on else '关'}")
