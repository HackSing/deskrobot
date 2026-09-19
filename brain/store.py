"""本地存储。C 负责。全部在 data/ 下，不上云。
- data/todos.sqlite     待办库
- data/preps/<项目>.json 会前准备
- data/meetings/<会议ID>/ minutes.json, transcript.txt
"""
from __future__ import annotations
import json
import os
import sqlite3
from pathlib import Path

from contracts import AgendaItem, Material, MeetingPrep, Minutes, Todo, Utterance, to_dict

DATA = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def _db() -> sqlite3.Connection:
    DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DATA / "todos.sqlite")
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS todos(
        id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT, owner TEXT, content TEXT,
        due TEXT, status TEXT DEFAULT 'open', confirmed INTEGER DEFAULT 0, meeting_id TEXT)""")
    return con


def add_todo(t: Todo) -> None:
    with _db() as con:
        con.execute("INSERT INTO todos(project,owner,content,due,status,confirmed,meeting_id) VALUES(?,?,?,?,?,?,?)",
                    (t.project, t.owner, t.content, t.due, t.status, int(t.confirmed), t.meeting_id))


def open_todos(project: str) -> list[Todo]:
    with _db() as con:
        rows = con.execute("SELECT * FROM todos WHERE project=? AND status='open' ORDER BY id", (project,)).fetchall()
    return [Todo(**{**dict(r), "confirmed": bool(r["confirmed"])}) for r in rows]


def set_todo_status(todo_id: int, status: str) -> None:
    with _db() as con:
        con.execute("UPDATE todos SET status=? WHERE id=?", (status, todo_id))


def save_prep(prep: MeetingPrep) -> None:
    d = DATA / "preps"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{prep.project}.json").write_text(json.dumps(to_dict(prep), ensure_ascii=False, indent=2), encoding="utf-8")


def load_prep(project: str) -> MeetingPrep | None:
    """按项目名找会前准备。找不到完全相同的，就找名字互相包含的。"""
    d = DATA / "preps"
    if not d.exists():
        return None
    files = {p.stem: p for p in d.glob("*.json")}
    hit = files.get(project) or next((p for name, p in files.items() if name in project or project in name), None)
    if not hit:
        return None
    raw = json.loads(hit.read_text(encoding="utf-8"))
    return MeetingPrep(project=raw["project"], agenda=[AgendaItem(**a) for a in raw.get("agenda", [])],
                       participants=raw.get("participants", []), background=raw.get("background", ""),
                       materials=[Material(**m) for m in raw.get("materials", [])])


def list_preps() -> list[str]:
    d = DATA / "preps"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


def save_meeting(meeting_id: str, project: str, minutes: Minutes, transcript: list[Utterance]) -> None:
    d = DATA / "meetings" / meeting_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "minutes.json").write_text(
        json.dumps({"meeting_id": meeting_id, "project": project, **to_dict(minutes)}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    (d / "transcript.txt").write_text("\n".join(u.text for u in transcript), encoding="utf-8")
    for t in minutes.todos:
        add_todo(t)


def history(project: str, limit: int = 5) -> list[dict]:
    d = DATA / "meetings"
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("*/minutes.json"), reverse=True):
        m = json.loads(p.read_text(encoding="utf-8"))
        if m.get("project") == project:
            out.append(m)
        if len(out) >= limit:
            break
    return out


def latest_minutes() -> dict | None:
    d = DATA / "meetings"
    files = sorted(d.glob("*/minutes.json"), reverse=True) if d.exists() else []
    return json.loads(files[0].read_text(encoding="utf-8")) if files else None
