"""Web 层：/h5 托管前端构建产物、/h5-lite 保底页、/ws 能连上并先收到一条完整快照。
/ws 依赖 websockets 库（requirements.txt 里有）；缺了这个库 uvicorn 会悄悄拒绝所有 WebSocket 连接。"""
import os, sys, pathlib, tempfile
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

from fastapi.testclient import TestClient

from core.orchestrator import Orchestrator
from mocks.fake_brain import FakeBrain
from mocks.fake_robot import FakeRobot
from mocks.fake_speech import FakeSpeech
from web.server import STATIC, build_app


def _client() -> TestClient:
    orch = Orchestrator(FakeSpeech(read_stdin=False), FakeRobot(), FakeBrain(), "小登")
    return TestClient(build_app(orch))


def test_h5_pages():
    c = _client()
    r = c.get("/h5-lite")
    assert r.status_code == 200 and "<html" in r.text
    r = c.get("/h5/", follow_redirects=True)
    assert r.status_code == 200 and "<html" in r.text
    if (STATIC / "h5" / "index.html").exists():          # 构建产物在：/h5 是 React 页，资源路径带 /h5/
        assert 'id="root"' in r.text and "/h5/assets/" in r.text


def test_ws_first_message_is_snapshot():
    c = _client()
    with c.websocket_connect("/ws") as ws:
        snap = ws.receive_json()
    assert snap["state"] == "idle" and snap["robot_name"] == "小登" and "minutes" in snap
    assert c.get("/api/state").json()["state"] == "idle"
