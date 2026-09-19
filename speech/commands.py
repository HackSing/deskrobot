"""在一句转写文本里找 [名字] + 指令词。B 负责。纯函数，有单元测试。"""
from __future__ import annotations
import re
import time

from contracts import Command

# 顺序有意义：先匹配更具体的
_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("start", re.compile(r"(开始|开个|开一下).{0,12}(会议|开会|的会)|开会")),
    ("end", re.compile(r"(会议|开会)?(结束|散会)|结束会议")),
    ("mark", re.compile(r"(记下|记一下|记住|标记)(这个|一下)?(重点|要点)?[:：，,]?\s*(?P<arg>.*)")),
    ("ask", re.compile(r"(?P<arg>.+)")),                      # 叫了名字但不是以上指令 = 提问
]
_PUNCT = " ，,。.！!？?：:、"


def match_command(text: str, robot_name: str) -> Command | None:
    """没叫名字返回 None。名字后面的内容按规则归类，兜底归为 ask。"""
    pos = text.find(robot_name)
    if pos < 0:
        return None
    rest = text[pos + len(robot_name):].strip(_PUNCT)
    if not rest:
        return None
    for name, pat in _RULES:
        m = pat.search(rest) if name != "ask" else pat.match(rest)
        if m:
            arg = (m.groupdict().get("arg") or "").strip(_PUNCT)
            if name == "ask":
                arg = rest
            return Command(name=name, arg=arg, raw=text, ts=time.time())
    return None
