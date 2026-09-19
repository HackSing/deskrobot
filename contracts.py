"""全队共用的接口。只有 A 可以改这个文件；其他人要改先在群里说。

数据流：
  speech  --Utterance-->  core  --cue/say-->  robot_io / speech
                           |--调用--> brain（纯函数，不碰硬件）
                           |--快照--> web（看板）
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Awaitable, Callable, Literal, Protocol

# ---------- 指令 ----------
CommandName = Literal["start", "end", "mark", "ask"]
COMMANDS: tuple[str, ...] = ("start", "end", "mark", "ask")

# ---------- 机器人反馈（表情 + 灯光 + 动作的组合，由 robot_io 翻译成 SDK 调用）----------
CueName = Literal[
    "standby",          # 待机：闭眼，灯灭
    "meeting_start",    # 开场：聆听，侧灯亮，底灯绿
    "idle",             # 会中安静听
    "mark",             # 记重点：点头，侧灯闪一次
    "thinking",         # 找答案中：thinking，侧灯脉冲
    "speaking",         # 说话中
    "off_topic_soft",   # 跑题第一次：无语表情，不出声
    "off_topic_speak",  # 跑题连续两次：疑问表情，准备开口
    "overtime",         # 超时：吃惊，底灯红闪
    "confirm_ask",      # 逐条确认待办：疑问，侧灯呼吸
    "confirm_ok",       # 待办已确认：开心，侧灯绿闪
    "loud",             # 音量过高：低头
]
CUES: tuple[str, ...] = (
    "standby", "meeting_start", "idle", "mark", "thinking", "speaking",
    "off_topic_soft", "off_topic_speak", "overtime", "confirm_ask", "confirm_ok", "loud",
)

AnswerSource = Literal["materials", "transcript", "history", "web", "none"]
SOURCE_LABEL = {"materials": "会议资料", "transcript": "本场转写", "history": "历史纪要", "web": "联网", "none": "没找到"}


# ---------- 数据 ----------
@dataclass
class Utterance:
    text: str
    ts: float                      # time.time()


@dataclass
class Command:
    name: str                      # COMMANDS 之一
    arg: str                       # 指令词后面的内容，可为空
    raw: str
    ts: float


@dataclass
class AgendaItem:
    title: str
    minutes: float


@dataclass
class Material:
    filename: str
    text: str


@dataclass
class MeetingPrep:
    project: str
    agenda: list[AgendaItem] = field(default_factory=list)
    participants: list[str] = field(default_factory=list)
    background: str = ""
    materials: list[Material] = field(default_factory=list)

    @property
    def total_minutes(self) -> float:
        return sum(a.minutes for a in self.agenda)


@dataclass
class OpeningInfo:
    project: str | None
    total_minutes: float | None
    agenda_count: int | None


@dataclass
class Todo:
    project: str
    owner: str
    content: str
    due: str = ""
    status: str = "open"           # open / done
    confirmed: bool = False
    meeting_id: str = ""
    id: int | None = None


@dataclass
class Answer:
    text: str                      # 不超过两句话
    source: str                    # AnswerSource


@dataclass
class Minutes:
    conclusions: list[str] = field(default_factory=list)
    todos: list[Todo] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)


@dataclass
class Context:
    """问答和出纪要时给大脑的全部上下文。"""
    prep: MeetingPrep | None
    transcript: list[Utterance]
    history: list[dict]            # 同项目历史纪要（Minutes 的 dict 形式）


def to_dict(obj) -> dict:
    return asdict(obj)


# ---------- 模块接口 ----------
OnUtterance = Callable[[Utterance], Awaitable[None]]
OnTouch = Callable[[str], Awaitable[None]]      # "back_press" / "back_long" / "roller+1" / "roller-1" / "screen_tap"


class SpeechIO(Protocol):
    """B 负责。真实现 speech/real.py，假实现 mocks/fake_speech.py。"""
    async def run(self, on_utterance: OnUtterance) -> None: ...   # 一直跑，每识别出一句就回调
    async def say(self, text: str) -> None: ...                   # 播报；播报期间不得回调 on_utterance


class RobotIO(Protocol):
    """A 负责。真实现 robot_io/real.py，假实现 mocks/fake_robot.py。"""
    async def cue(self, name: str) -> None: ...
    async def set_progress(self, ratio: float) -> None: ...       # 0~1 绿到黄，>1 红；负数 = 关底灯
    async def run_inputs(self, on_touch: OnTouch) -> None: ...     # 一直跑
    async def face_tracking(self, on: bool) -> None: ...


class Brain(Protocol):
    """C 负责。真实现 brain/real.py，假实现 mocks/fake_brain.py。"""
    async def parse_opening(self, text: str) -> OpeningInfo: ...
    async def answer(self, question: str, ctx: Context) -> Answer: ...
    async def is_off_topic(self, agenda: list[AgendaItem], current: int, recent: list[Utterance]) -> bool: ...
    async def make_minutes(self, ctx: Context, marks: list[str]) -> Minutes: ...
