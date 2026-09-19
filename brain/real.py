"""真大脑：调 OpenAI 兼容的 chat/completions 接口。C 负责。
换供应方只改 .env：LLM_URL、LLM_KEY、LLM_MODEL；联网搜索的额外参数放 LLM_SEARCH_EXTRA（JSON）。
"""
from __future__ import annotations
import json
import os
import re

import httpx

from contracts import AgendaItem, Answer, Context, Minutes, OpeningInfo, Todo, Utterance
from brain import prompts

LLM_URL = os.environ.get("LLM_URL", "")
LLM_KEY = os.environ.get("LLM_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "")
SEARCH_EXTRA = json.loads(os.environ.get("LLM_SEARCH_EXTRA", "{}") or "{}")     # 例：{"enable_search": true}
RECENT_KEEP_SECONDS = 15 * 60
WEB_HINTS = ("查一下", "查查", "搜一下", "联网")


def _fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace("{" + k + "}", str(v))
    return template


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


class RealBrain:
    def __init__(self) -> None:
        self.http = httpx.AsyncClient(timeout=40)

    async def _chat(self, prompt: str, extra: dict | None = None) -> str:
        body = {"model": LLM_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, **(extra or {})}
        r = await self.http.post(LLM_URL, headers={"Authorization": f"Bearer {LLM_KEY}"}, json=body)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    async def parse_opening(self, text: str) -> OpeningInfo:
        d = _json(await self._chat(_fill(prompts.PARSE_OPENING, text=text)))
        return OpeningInfo(d.get("project"), d.get("total_minutes"), d.get("agenda_count"))

    async def answer(self, question: str, ctx: Context) -> Answer:
        recent = " / ".join(u.text for u in ctx.transcript[-8:])
        if not any(h in question for h in WEB_HINTS):
            d = _json(await self._chat(_fill(
                prompts.ANSWER, question=question, background=ctx.prep.background if ctx.prep else "",
                materials=_materials(ctx), history=json.dumps(ctx.history, ensure_ascii=False)[:6000],
                transcript=_transcript(ctx.transcript))))
            if d.get("text") and d.get("source") in ("materials", "transcript", "history"):
                return Answer(d["text"], d["source"])
        try:
            text = await self._chat(_fill(prompts.ANSWER_WEB, question=question, recent=recent), extra=SEARCH_EXTRA)
            return Answer(text.strip(), "web")
        except Exception:
            return Answer("这个我没找到。", "none")

    async def is_off_topic(self, agenda: list[AgendaItem], current: int, recent: list[Utterance]) -> bool:
        d = _json(await self._chat(_fill(
            prompts.OFF_TOPIC, agenda="；".join(a.title for a in agenda),
            current=agenda[current].title if agenda else "", recent=" / ".join(u.text for u in recent))))
        return bool(d.get("off_topic"))

    async def make_minutes(self, ctx: Context, marks: list[str]) -> Minutes:
        d = _json(await self._chat(_fill(
            prompts.MINUTES, participants="、".join(ctx.prep.participants) if ctx.prep else "",
            marks=json.dumps(marks, ensure_ascii=False), materials=_materials(ctx)[:8000],
            transcript=_transcript(ctx.transcript, keep_all=True))))
        return Minutes(
            conclusions=d.get("conclusions", []), open_questions=d.get("open_questions", []),
            highlights=d.get("highlights", []) or marks,
            todos=[Todo(project="", owner=t.get("owner", ""), content=t.get("content", ""), due=t.get("due", ""))
                   for t in d.get("todos", [])])


def _materials(ctx: Context) -> str:
    if not ctx.prep:
        return ""
    return "\n\n".join(f"《{m.filename}》\n{m.text}" for m in ctx.prep.materials)


def _transcript(us: list[Utterance], keep_all: bool = False) -> str:
    # TODO(C)：转写过长时，保留最近 15 分钟原文，更早的部分压缩成摘要
    if not us:
        return ""
    cutoff = us[-1].ts - RECENT_KEEP_SECONDS
    return "\n".join(u.text for u in us if keep_all or u.ts >= cutoff)
