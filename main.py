"""组装。A 负责。每个模块可以单独切换真假：
  USE_FAKE_SPEECH=1  USE_FAKE_BRAIN=1  USE_FAKE_ROBOT=1
"""
from __future__ import annotations
import asyncio
import logging
import os

import uvicorn


def _load_env() -> None:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


_load_env()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


def _flag(name: str, default: bool) -> bool:
    return os.environ.get(name, "1" if default else "0") == "1"


async def run(sdk_robot=None) -> None:
    """sdk_robot = ApplicationContext.robot；为 None 时全部用假模块。"""
    from core.orchestrator import Orchestrator
    from web.server import build_app, lan_ip

    no_robot = sdk_robot is None
    if _flag("USE_FAKE_SPEECH", no_robot):
        from mocks.fake_speech import FakeSpeech
        speech = FakeSpeech()
    else:
        from speech.real import RealSpeech
        speech = RealSpeech(sdk_robot)
    if _flag("USE_FAKE_ROBOT", no_robot):
        from mocks.fake_robot import FakeRobot
        robot = FakeRobot()
    else:
        from robot_io.real import RealRobot
        robot = RealRobot(sdk_robot)
    if _flag("USE_FAKE_BRAIN", not os.environ.get("LLM_KEY")):
        from mocks.fake_brain import FakeBrain
        brain = FakeBrain()
    else:
        from brain.real import RealBrain
        brain = RealBrain()

    name = os.environ.get("ROBOT_NAME", "主持人")
    orch = Orchestrator(speech, robot, brain, name)
    port = int(os.environ.get("WEB_PORT", "8766"))
    server = uvicorn.Server(uvicorn.Config(build_app(orch), host="0.0.0.0", port=port, log_level="warning"))
    print(f"\n看板：http://{lan_ip()}:{port}   （本机：http://127.0.0.1:{port}）")
    print(f"语音={type(speech).__name__} 机器人={type(robot).__name__} 大脑={type(brain).__name__} 名字={name}\n")
    await asyncio.gather(orch.run(), server.serve())
