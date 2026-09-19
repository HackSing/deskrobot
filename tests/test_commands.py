import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from speech.commands import match_command

N = "主持人"

def name(text):
    c = match_command(text, N)
    return c.name if c else None

def test_no_name():
    assert name("我们开始开会吧") is None

def test_start():
    assert name("主持人，开始报价项目的会议，十分钟，两个议题") == "start"

def test_end():
    assert name("主持人，会议结束") == "end"
    assert name("好了主持人散会") == "end"

def test_mark():
    c = match_command("主持人，记下这个重点：B 家因起订量排除", N)
    assert c.name == "mark" and "B 家" in c.arg

def test_ask():
    c = match_command("主持人，资料里 A 家的交期是多少？", N)
    assert c.name == "ask" and "交期" in c.arg
    assert name("主持人，查一下这个芯片停产了吗") == "ask"
