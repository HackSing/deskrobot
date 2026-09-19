"""演示用大脑：包在真大脑（或假大脑）外面的一层。

和真大脑的区别只有三点，都是为了演示稳：
  1. 开场不解析，固定用 DEFAULT_PROJECT，顺手清空本场对话历史；
  2. 不判跑题；
  3. 纪要优先读 demo/mock_minutes.json（MINUTES_FROM_LLM=1 时改回真 LLM）。
问答仍然走真 LLM，而且是多轮的：资料 + 完整 mock 会议记录 + 历史纪要 + 本场对话历史。
inner 是假大脑时（没有 LLM_KEY），问答直接交给假大脑，保证没 key 也能演示。
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re

import httpx

from contracts import AgendaItem, Answer, Context, Minutes, OpeningInfo, Todo, Utterance

log = logging.getLogger("brain.demo")

DEMO_DIR = pathlib.Path(__file__).resolve().parent.parent / "demo"
MOCK_TRANSCRIPT = DEMO_DIR / "mock_transcript.json"
MOCK_MINUTES = DEMO_DIR / "mock_minutes.json"
HISTORY_TURNS = 10                 # 只保留最近 10 轮问答
HISTORY_CHARS = 3000               # 历史纪要截断
TIMEOUT = 20

SYSTEM = """你是会议室里的主持人机器人{name}。有人在会上叫你的名字问了一个问题。
规则：回答不超过两句话，口语，不要列表，不要编造；资料里没有就说没找到。允许追问，追问时结合上文。
只输出 JSON：{"text": "回答", "source": "materials" | "transcript" | "history" | "none"}

【会议资料】
{materials}

【会议记录】
{transcript}

【历史纪要】
{history}"""


def _fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def mock_transcript_lines() -> list[str]:
    """完整的 mock 会议记录，格式“张三：……”。不依赖状态机灌了多少条。"""
    try:
        rows = json.loads(MOCK_TRANSCRIPT.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("读不到 mock 会议记录：%s", e)
        return []
    return [f"{r.get('speaker', '')}：{r.get('text', '')}" for r in rows]


def mock_minutes() -> Minutes | None:
    """读 demo/mock_minutes.json。Todo 的 project/meeting_id 留空，由状态机填。"""
    try:
        d = json.loads(MOCK_MINUTES.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("读不到 mock 纪要：%s", e)
        return None
    return Minutes(
        conclusions=list(d.get("conclusions", [])),
        todos=[Todo(project="", owner=t.get("owner", ""), content=t.get("content", ""), due=t.get("due", ""))
               for t in d.get("todos", [])],
        open_questions=list(d.get("open_questions", [])),
        highlights=list(d.get("highlights", [])),
    )


def _materials(ctx: Context) -> str:
    if not ctx or not ctx.prep or not ctx.prep.materials:
        return "（没有资料）"
    return "\n\n".join(f"《{m.filename}》\n{m.text}" for m in ctx.prep.materials)


def _parse(text: str) -> tuple[str, str]:
    """先 json.loads，失败抓最外层大括号，再失败把原文当回答。"""
    candidates = [text]
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        candidates.append(m.group(0))
    for candidate in candidates:
        try:
            d = json.loads(candidate)
        except Exception:
            continue
        if isinstance(d, dict) and d.get("text"):
            src = d.get("source")
            return str(d["text"]).strip(), src if src in ("materials", "transcript", "history", "none") else "transcript"
    return text.strip(), "transcript"


class DemoBrain:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.history: list[dict] = []
        self.http = httpx.AsyncClient(timeout=TIMEOUT)

    # ---------- 演示里固定的三件事 ----------
    async def parse_opening(self, text: str) -> OpeningInfo:
        self.history = []
        return OpeningInfo(project=os.environ.get("DEFAULT_PROJECT", "供应商报价"),
                           total_minutes=None, agenda_count=None)

    async def is_off_topic(self, agenda: list[AgendaItem], current: int, recent: list[Utterance]) -> bool:
        return False

    async def make_minutes(self, ctx: Context, marks: list[str]) -> Minutes:
        if os.environ.get("MINUTES_FROM_LLM", "0") != "1":
            m = mock_minutes()
            if m is not None:
                return m
        return await self.inner.make_minutes(ctx, marks)

    # ---------- 问答：真 LLM 多轮 ----------
    async def answer(self, question: str, ctx: Context) -> Answer:
        if self._inner_is_fake():
            return await self.inner.answer(question, ctx)
        system = _fill(
            SYSTEM,
            name=os.environ.get("ROBOT_NAME", "小登"),
            materials=_materials(ctx),
            transcript="\n".join(mock_transcript_lines()),
            history=json.dumps(ctx.history if ctx else [], ensure_ascii=False)[:HISTORY_CHARS],
        )
        messages = [{"role": "system", "content": system}, *self.history, {"role": "user", "content": question}]
        try:
            raw = await self._chat(messages)
            text, source = _parse(raw)
            if not text:                       # json 模式偶尔只回空白，退回普通模式再问一次
                log.warning("演示问答返回空白，改用非 json 模式重试")
                text, source = _parse(await self._chat(messages, json_mode=False))
        except Exception as e:
            log.warning("演示问答失败：%s", e)
            return Answer("这个我没找到。", "none")
        if not text:
            return Answer("这个我没找到。", "none")
        # 历史里的 assistant 存 JSON 原文：json 模式下如果历史里的回答是纯文本，
        # DeepSeek 会只回空白（实测）。存 JSON 既能续上下文，又不会破坏 json 模式。
        self.history += [{"role": "user", "content": question},
                         {"role": "assistant", "content": json.dumps({"text": text, "source": source},
                                                                     ensure_ascii=False)}]
        self.history = self.history[-HISTORY_TURNS * 2:]
        return Answer(text, source)

    async def _chat(self, messages: list[dict], json_mode: bool = True) -> str:
        # LLM_EXTRA：推理模型要在这里关思考（{"thinking": {"type": "disabled"}}），否则 content 是空串。
        extra = json.loads(os.environ.get("LLM_EXTRA", "{}") or "{}")
        body = {"model": os.environ.get("LLM_MODEL", ""), "messages": messages, "temperature": 0.2, **extra}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        r = await self.http.post(os.environ.get("LLM_URL", ""),
                                 headers={"Authorization": f"Bearer {os.environ.get('LLM_KEY', '')}"},
                                 json=body)
        if r.status_code >= 400:                  # 把接口的原话带出来，现场好排查
            raise RuntimeError(f"HTTP {r.status_code} {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"] or ""

    def _inner_is_fake(self) -> bool:
        try:
            from mocks.fake_brain import FakeBrain
        except Exception:
            return False
        return isinstance(self.inner, FakeBrain)
