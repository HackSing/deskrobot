"""假大脑：不联网、不花钱，用正则和关键词给出像样的结果。够把整条链路串通。"""
from __future__ import annotations
import re

from contracts import AgendaItem, Answer, Context, Minutes, OpeningInfo, Todo, Utterance

_CN = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "十": 10, "半": 0.5}
_OFF = ("吃什么", "午饭", "外卖", "奶茶", "周末去哪", "电影")


def _num(s: str) -> float | None:
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    return _CN.get(s)


class FakeBrain:
    async def parse_opening(self, text: str) -> OpeningInfo:
        proj = re.search(r"开始(.{1,12}?)(项目)?的?(会议|会)", text)
        mins = re.search(r"(\d+|[一两二三四五十半])\s*(分钟|个?小时)", text)
        cnt = re.search(r"(\d+|[一两二三四五])\s*个议题", text)
        total = _num(mins.group(1)) if mins else None
        if total and mins and "小时" in mins.group(2):
            total *= 60
        return OpeningInfo(proj.group(1).strip() if proj else None, total, int(_num(cnt.group(1))) if cnt else None)

    async def answer(self, question: str, ctx: Context) -> Answer:
        keys = [k for k in re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fa5]{2}", question) if k not in ("资料", "多少", "什么")]
        for label, lines in (
            ("materials", [(m.filename, ln) for m in (ctx.prep.materials if ctx.prep else []) for ln in m.text.splitlines()]),
            ("transcript", [("", u.text) for u in ctx.transcript[:-1]]),
        ):
            best = max(lines, key=lambda x: sum(k in x[1] for k in keys), default=None)
            if best and sum(k in best[1] for k in keys) >= 2:
                where = f"（{best[0]}）" if best[0] else ""
                return Answer(f"{best[1].strip()}{where}。", label)
        if "查" in question:
            return Answer("（假大脑不能联网）查到的结果会在这里，用两句话说完。", "web")
        return Answer("这个我没找到。", "none")

    async def is_off_topic(self, agenda: list[AgendaItem], current: int, recent: list[Utterance]) -> bool:
        return any(w in u.text for u in recent for w in _OFF)

    async def make_minutes(self, ctx: Context, marks: list[str]) -> Minutes:
        names = ctx.prep.participants if ctx.prep and ctx.prep.participants else ["张三", "李四", "王五"]
        todos, conclusions = [], []
        for u in ctx.transcript:
            m = re.search(rf"({'|'.join(map(re.escape, names))})[，,]?(.*?(?:今天|明天|周[一二三四五六日天]|下周.?|月底)前?)(.+)", u.text)
            if m and "主持人" not in u.text:
                todos.append(Todo(project="", owner=m.group(1), due=m.group(2).strip(), content=m.group(3).strip("，。 ")))
            elif re.search(r"(就定|决定|结论是|那就)", u.text):
                conclusions.append(u.text)
        return Minutes(conclusions=conclusions or ["（假大脑）本场没有识别到明确结论"], todos=todos,
                       open_questions=[], highlights=list(marks))
