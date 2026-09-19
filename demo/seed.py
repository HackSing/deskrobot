"""预置一条上次会议留下的待办，用来演示“开场追待办”。"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from brain import store
from contracts import Todo

store.add_todo(Todo(project="供应商报价", owner="张三", content="供应商报价还没结", meeting_id="seed"))
print("已预置：张三的供应商报价还没结")
