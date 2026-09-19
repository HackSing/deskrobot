"""真机器人。A 负责。所有 SDK 调用都是阻塞的，必须包在 asyncio.to_thread 里。"""
from __future__ import annotations
import asyncio
import logging

from contracts import OnTouch
from robot_io.cues import CUE_TABLE, progress_color

log = logging.getLogger("robot")


class RealRobot:
    def __init__(self, robot) -> None:            # robot = ApplicationContext.robot
        self.r = robot
        self._bottom: tuple | None = None
        self._tracking = False

    async def _try(self, fn, *args, **kw):
        try:
            return await asyncio.to_thread(fn, *args, **kw)
        except Exception as e:                    # 演示时硬件报错不能让状态机崩
            log.warning("robot call failed: %s %s", getattr(fn, "__qualname__", fn), e)

    async def cue(self, name: str) -> None:
        spec = CUE_TABLE.get(name)
        if not spec:
            return
        color, effect = spec["side"]
        if color == "off":
            await self._try(self.r.lights.set_color, "#000000", brightness=0.0, zone="side")
        elif color and effect:
            await self._try(self.r.lights.play_effect, effect, color=color, zone="side", period_ms=700, repeat=0)
        elif color:
            await self._try(self.r.lights.set_color, color, zone="side")
        if spec.get("behavior"):
            await self._try(self.r.behavior.play, spec["behavior"], repeat=1)     # 不等播完
        for deg in spec.get("tilt", []):
            job = await self._try(self.r.motion.move_to, pan_deg=0, tilt_deg=deg, duration_ms=300)
            if job:
                await self._try(job.wait, 2.0)
            # TODO(A)：跟随开启时云台归跟随服务管，点头前后可能要暂停跟随

    async def set_progress(self, ratio: float) -> None:
        state = ("off", None) if ratio < 0 else progress_color(ratio)
        if state == self._bottom:                 # 颜色没变就不重复发命令
            return
        self._bottom = state
        color, effect = state
        if color == "off":
            await self._try(self.r.lights.set_color, "#000000", brightness=0.0, zone="bottom")
        elif effect:
            await self._try(self.r.lights.play_effect, effect, color=color, zone="bottom", period_ms=500, repeat=0)
        else:
            await self._try(self.r.lights.set_color, color, zone="bottom")

    async def run_inputs(self, on_touch: OnTouch) -> None:
        while True:
            try:
                ev = await asyncio.to_thread(self.r.inputs.wait, 1.0)
            except TimeoutError:
                continue
            except Exception as e:                # TODO(A)：确认 inputs.wait 超时抛什么
                log.debug("inputs.wait: %s", e)
                await asyncio.sleep(0.2)
                continue
            src = getattr(ev, "source", "")
            if src == "back_touch":
                if ev.action == "press":
                    await on_touch("back_press")
                elif ev.action == "long_press":
                    await on_touch("back_long")
            elif src == "roller":
                await on_touch("roller+1" if ev.delta > 0 else "roller-1")
            elif src == "screen_touch":
                await on_touch("screen_tap")

    async def face_tracking(self, on: bool) -> None:
        if not self.r.supports("face_tracking.control.v1"):
            return
        if on and not self._tracking:
            await self._try(self.r.face_tracking.start, timeout=10.0)    # 首次启动约 6 秒
            self._tracking = True
        elif not on and self._tracking:
            await self._try(self.r.face_tracking.stop)
            self._tracking = False
