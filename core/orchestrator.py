"""会议状态机。A 负责。

状态：idle -> meeting -> confirming -> idle
它不直接碰硬件、不直接调云服务，只通过 contracts 里的三个接口做事。
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid

from contracts import (
    SOURCE_LABEL, Brain, Context, MeetingPrep, AgendaItem, Minutes, RobotIO, SpeechIO, Utterance, to_dict,
)
from core.bus import Broadcaster
from speech.commands import match_command
from brain import store

OFF_TOPIC_EVERY = float(os.environ.get("OFF_TOPIC_EVERY", "30"))   # 秒
CONFIRM_WAIT = float(os.environ.get("CONFIRM_WAIT", "8"))           # 每条待办等拍背的秒数
DEFAULT_PROJECT = os.environ.get("DEFAULT_PROJECT", "默认项目")


class Orchestrator:
    def __init__(self, speech: SpeechIO, robot: RobotIO, brain: Brain, robot_name: str) -> None:
        self.speech, self.robot, self.brain, self.name = speech, robot, brain, robot_name
        self.bus = Broadcaster()
        self.state = "idle"
        self.prep: MeetingPrep | None = None
        self.meeting_id = ""
        self.transcript: list[Utterance] = []
        self.marks: list[str] = []
        self.minutes: Minutes | None = None
        self.last_answer: dict | None = None
        self.started_at = 0.0
        self._half_done = self._over_done = False
        self._item_over: set[int] = set()
        self._off_topic_hits = 0
        self._last_off_check = 0.0
        self._touch: asyncio.Event = asyncio.Event()
        self._busy = asyncio.Lock()           # 同一时刻只处理一条指令

    # ---------- 入口 ----------
    async def run(self) -> None:
        await self.robot.cue("standby")
        await self.robot.set_progress(-1)
        await asyncio.gather(
            self.speech.run(self.on_utterance),
            self.robot.run_inputs(self.on_touch),
            self._ticker(),
        )

    async def on_utterance(self, u: Utterance) -> None:
        if self.state == "meeting":
            self.transcript.append(u)
            await self._publish()
        cmd = match_command(u.text, self.name)
        if cmd is None:
            return
        async with self._busy:
            if cmd.name == "start" and self.state == "idle":
                await self._start(cmd.raw)
            elif cmd.name == "mark" and self.state == "meeting":
                await self._mark(cmd.arg)
            elif cmd.name == "ask" and self.state == "meeting":
                await self._ask(cmd.arg)
            elif cmd.name == "end" and self.state == "meeting":
                await self._end()

    async def on_touch(self, kind: str) -> None:
        if kind == "back_press":
            self._touch.set()
        elif kind == "back_long" and self.state == "meeting":      # 长按 = 语音结束的备份
            async with self._busy:
                await self._end()

    # ---------- 指令 ----------
    async def _start(self, raw: str) -> None:
        info = await self.brain.parse_opening(raw)
        project = info.project or DEFAULT_PROJECT
        self.prep = store.load_prep(project) or MeetingPrep(
            project=project,
            agenda=[AgendaItem(f"议题 {i + 1}", (info.total_minutes or 30) / (info.agenda_count or 1))
                    for i in range(info.agenda_count or 1)],
        )
        self.meeting_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4]
        self.transcript, self.marks, self.minutes, self.last_answer = [], [], None, None
        self._half_done = self._over_done = False
        self._item_over, self._off_topic_hits = set(), 0
        self.started_at = self._last_off_check = time.time()
        self.state = "meeting"
        await self.robot.face_tracking(True)
        await self.robot.cue("meeting_start")
        await self.robot.set_progress(0)
        todos = store.open_todos(project)
        text = f"{project}会议开始，共 {self.prep.total_minutes:g} 分钟。"
        if todos:
            text += f"上次遗留 {len(todos)} 项：" + "；".join(f"{t.owner}的{t.content}" for t in todos[:3]) + "。"
        if self.prep.materials:
            text += f"今天的 {len(self.prep.materials)} 份资料我看过了。"
        await self._say(text)

    async def _mark(self, arg: str) -> None:
        content = arg or (self.transcript[-2].text if len(self.transcript) >= 2 else "")
        if content:
            self.marks.append(content)
        await self.robot.cue("mark")
        await self.robot.cue("idle")
        await self._publish()

    async def _ask(self, question: str) -> None:
        await self.robot.cue("thinking")
        ans = await self.brain.answer(question, self._context())
        self.last_answer = {"question": question, "text": ans.text, "source": ans.source}
        label = SOURCE_LABEL.get(ans.source, ans.source)
        await self._say(ans.text if ans.source == "none" else f"{ans.text}来源：{label}。")

    async def _end(self) -> None:
        self.state = "confirming"
        await self.robot.cue("thinking")
        self.minutes = await self.brain.make_minutes(self._context(), self.marks)
        for todo in self.minutes.todos:
            todo.project, todo.meeting_id = self.prep.project, self.meeting_id
            self._touch.clear()                   # 播报期间拍背也算数
            await self._say(f"{todo.owner}，{todo.due}{todo.content}，对吗？")
            await self.robot.cue("confirm_ask")
            try:
                await asyncio.wait_for(self._touch.wait(), CONFIRM_WAIT)
                todo.confirmed = True
                await self.robot.cue("confirm_ok")
            except asyncio.TimeoutError:
                pass
            await self._publish()
        store.save_meeting(self.meeting_id, self.prep.project, self.minutes, self.transcript)
        await self._say(f"{len(self.minutes.conclusions)} 条结论，{len(self.minutes.todos)} 条待办，已保存。")
        await self.robot.face_tracking(False)
        await self.robot.set_progress(-1)
        await self.robot.cue("standby")
        self.state = "idle"
        await self._publish()

    # ---------- 定时 ----------
    async def _ticker(self) -> None:
        while True:
            await asyncio.sleep(1)
            if self.state != "meeting" or not self.prep:
                continue
            ratio = self.elapsed / max(self.prep.total_minutes * 60, 1)
            await self.robot.set_progress(ratio)
            idx = self.current_item
            item_end = sum(a.minutes for a in self.prep.agenda[: idx + 1]) * 60
            if self._busy.locked():
                continue
            if ratio >= 1 and not self._over_done:
                self._over_done = True
                async with self._busy:
                    await self.robot.cue("overtime")
                    await self._say("会议已经超时了。")
            elif self.elapsed > item_end and idx not in self._item_over and idx < len(self.prep.agenda) - 1:
                self._item_over.add(idx)
                async with self._busy:
                    await self.robot.cue("overtime")
                    await self._say(f"“{self.prep.agenda[idx].title}”这个议题超时了。")
            elif time.time() - self._last_off_check >= OFF_TOPIC_EVERY:
                self._last_off_check = time.time()
                await self._check_off_topic()
            await self._publish()

    async def _check_off_topic(self) -> None:
        recent = [u for u in self.transcript if u.ts >= time.time() - OFF_TOPIC_EVERY]
        if len(recent) < 2:
            return
        if await self.brain.is_off_topic(self.prep.agenda, self.current_item, recent):
            self._off_topic_hits += 1
            if self._off_topic_hits == 1:
                await self.robot.cue("off_topic_soft")
            else:
                async with self._busy:
                    await self.robot.cue("off_topic_speak")
                    await self._say("这个要不要会后聊？")
                self._off_topic_hits = 0
        else:
            self._off_topic_hits = 0

    # ---------- 工具 ----------
    async def _say(self, text: str) -> None:
        await self.robot.cue("speaking")
        self.last_said = text
        await self._publish()
        await self.speech.say(text)
        await self.robot.cue("standby" if self.state == "idle" else "idle")

    def _context(self) -> Context:
        return Context(prep=self.prep, transcript=list(self.transcript),
                       history=store.history(self.prep.project) if self.prep else [])

    @property
    def elapsed(self) -> float:
        return time.time() - self.started_at if self.state != "idle" else 0.0

    @property
    def current_item(self) -> int:
        if not self.prep:
            return 0
        acc = 0.0
        for i, a in enumerate(self.prep.agenda):
            acc += a.minutes * 60
            if self.elapsed < acc:
                return i
        return max(len(self.prep.agenda) - 1, 0)

    def snapshot(self) -> dict:
        p = self.prep
        return {
            "state": self.state, "robot_name": self.name, "meeting_id": self.meeting_id,
            "project": p.project if p else None,
            "agenda": [to_dict(a) for a in p.agenda] if p else [],
            "current_item": self.current_item, "elapsed": round(self.elapsed),
            "total": round(p.total_minutes * 60) if p else 0,
            "materials": [m.filename for m in p.materials] if p else [],
            "transcript": [to_dict(u) for u in self.transcript[-50:]],
            "marks": self.marks, "last_answer": self.last_answer,
            "last_said": getattr(self, "last_said", ""),
            "minutes": to_dict(self.minutes) if self.minutes else None,
        }

    async def _publish(self) -> None:
        await self.bus.publish(self.snapshot())
