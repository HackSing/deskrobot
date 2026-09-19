"""用假模块把整场会议跑一遍：开场、记重点、提问、结束、拍背确认。"""
import asyncio, os, sys, pathlib, tempfile, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["CONFIRM_WAIT"] = "0.3"

from contracts import AgendaItem, Material, MeetingPrep, Todo, Utterance
from brain import store
from core.orchestrator import Orchestrator
from mocks.fake_brain import FakeBrain
from mocks.fake_robot import FakeRobot
from mocks.fake_speech import FakeSpeech


def test_full_meeting():
    async def go():
        store.save_prep(MeetingPrep("报价", [AgendaItem("对比供应商", 1), AgendaItem("下一步", 1)], ["张三", "李四"],
                                    materials=[Material("对比表.md", "A 家交期 45 天\nC 家交期 30 天")]))
        store.add_todo(Todo("报价", "张三", "供应商报价"))
        speech = FakeSpeech(read_stdin=False)
        orch = Orchestrator(speech, FakeRobot(), FakeBrain(), "主持人")
        said = []
        orig = speech.say
        async def say(t): said.append(t); await orig(t)
        speech.say = say
        u = lambda t: orch.on_utterance(Utterance(t, time.time()))
        await u("主持人，开始报价项目的会议")
        assert orch.state == "meeting" and "张三的供应商报价" in said[0]
        await u("主持人，记下这个重点：B 家排除")
        await u("主持人，资料里 A 家的交期是多少")
        assert orch.last_answer["source"] == "materials" and "45" in orch.last_answer["text"]
        await u("李四，周五前拿到 A 家的正式报价")
        await u("主持人，会议结束")
        assert orch.state == "idle" and len(orch.minutes.todos) == 1
        assert store.latest_minutes()["highlights"] == ["B 家排除"]
        assert len(store.open_todos("报价")) == 2
    asyncio.run(go())
