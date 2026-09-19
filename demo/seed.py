"""演示用的预置数据：会前准备（议程、参会人、资料）+ 一条上次会议留下的待办。

两种用法：
  python demo/seed.py        直接跑一遍
  from demo.seed import seed_demo; seed_demo()    DEMO_MODE 启动时自动跑
幂等：重复调用不会重复插待办。
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from brain import store
from contracts import AgendaItem, Material, MeetingPrep, Todo

DEMO_DIR = pathlib.Path(__file__).resolve().parent
PROJECT = "供应商报价"
MATERIAL_NAME = "演示资料_供应商对比表.md"
BACKGROUND = "新产品首批计划 1500 台，10 月底前要拿到样品。今天要在 A、B、C 三家供应商里定下这一轮先谈谁。"
LEFTOVER_TODO = Todo(project=PROJECT, owner="张三", content="供应商报价还没结", meeting_id="seed")


def _material() -> list[Material]:
    path = DEMO_DIR / MATERIAL_NAME
    if not path.exists():
        return []
    return [Material(MATERIAL_NAME, path.read_text(encoding="utf-8"))]


def seed_demo() -> None:
    """预置会前准备和上次遗留待办。可以重复调用。"""
    store.save_prep(MeetingPrep(
        project=PROJECT,
        agenda=[AgendaItem("对比三家供应商", 10), AgendaItem("定下一步动作", 10)],
        participants=["张三", "李四", "王五"],
        background=BACKGROUND,
        materials=_material(),
    ))
    if not store.open_todos(PROJECT):
        store.add_todo(LEFTOVER_TODO)


if __name__ == "__main__":
    seed_demo()
    print(f"已预置：{PROJECT} 的会前准备（{len(_material())} 份资料）"
          f"，待办 {len(store.open_todos(PROJECT))} 条")
