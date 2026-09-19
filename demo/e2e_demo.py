"""端到端联调：假 H5 接收端 + 真后端（run_local.py，读根目录 .env）+ HTTP 驱动整场演示。

用法（在仓库任意位置）：python demo/e2e_demo.py
会做的事：起一个本地接收端收推送；用当前 .env 启动后端；依次说开始、两次提问、结束；
打印每步关键字段和收到的推送事件；最后杀掉后端。不需要机器人，不需要对方前端。
如果 .env 里已经填了 H5_PUSH_URL，推送会发去那个地址，本地接收端收不到，脚本只检查流程不检查推送。
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8766
HOOK_PORT = 8799
BASE = f"http://127.0.0.1:{PORT}"

received: list[dict] = []


class Hook(BaseHTTPRequestHandler):
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        received.append(json.loads(self.rfile.read(n) or b"{}"))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a):
        pass


def _dotenv_has_push_url() -> bool:
    env = ROOT / ".env"
    if not env.exists():
        return False
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("H5_PUSH_URL=") and line.split("=", 1)[1].strip():
            return True
    return False


def main() -> int:
    check_push = not _dotenv_has_push_url()
    srv = HTTPServer(("127.0.0.1", HOOK_PORT), Hook)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    env = dict(os.environ)
    env.update({
        "DATA_DIR": tempfile.mkdtemp(prefix="deskrobot_e2e_"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
    })
    if check_push:
        env["H5_PUSH_URL"] = f"http://127.0.0.1:{HOOK_PORT}/hook"
    else:
        print("提示：.env 里已有 H5_PUSH_URL，推送会发去那里，本脚本不检查推送。")
    flags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    proc = subprocess.Popen([sys.executable, "run_local.py"], cwd=ROOT, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                            encoding="utf-8", errors="replace", creationflags=flags)
    log_lines: list[str] = []
    threading.Thread(target=lambda: [log_lines.append(l.rstrip()) for l in proc.stdout], daemon=True).start()

    c = httpx.Client(timeout=10)
    try:
        for _ in range(40):
            try:
                c.get(BASE + "/api/state")
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("后端没起来。日志：\n" + "\n".join(log_lines[-30:]))
            return 1

        def say(text: str, wait: float):
            t0 = time.time()
            c.post(BASE + "/api/debug/say", json={"text": text})
            time.sleep(wait)
            return c.get(BASE + "/api/state").json(), time.time() - t0

        s = c.get(BASE + "/api/state").json()
        print("启动快照：state=%s demo=%s materials=%s" % (s.get("state"), s.get("demo"), s.get("materials")))

        s, _ = say("小登，开始会议", 6)
        print("\n[开始] state=%s project=%s agenda=%s" % (s["state"], s["project"], [a["title"] for a in s["agenda"]]))
        print("       开场白：%s" % s.get("last_said"))
        print("       转写已灌 %d 条" % len(s["transcript"]))

        for q in ("小登，资料里 A 家和 C 家的交期分别是多少", "小登，那 B 家呢"):
            s, dt = say(q, 12)
            la = s.get("last_answer") or {}
            print("\n[提问] %s" % q)
            print("       回答：%s  来源=%s  （含等待 %.0fs）" % (la.get("text"), la.get("source"), dt))

        s, _ = say("小登，会议结束", 8)
        m = s.get("minutes") or {}
        print("\n[结束] state=%s 结束语：%s" % (s["state"], s.get("last_said")))
        print("       纪要：结论 %d 条，待办 %d 条，未决 %d 条，重点 %d 条" % (
            len(m.get("conclusions", [])), len(m.get("todos", [])),
            len(m.get("open_questions", [])), len(m.get("highlights", []))))
        for t in m.get("todos", []):
            print("       待办：%s %s %s confirmed=%s" % (t.get("owner"), t.get("due"), t.get("content"), t.get("confirmed")))

        time.sleep(1)
        events = [r.get("event") for r in received]
        push_ok = True
        if check_push:
            dedup = [e for i, e in enumerate(events) if i == 0 or e != events[i - 1]]
            ended = [r for r in received if r.get("event") == "meeting_ended"]
            print("\n[推送] 共收到 %d 条，事件序列（去连续重复）：" % len(events))
            print("       " + " > ".join(dedup))
            print("       meeting_ended 的 data.minutes 非空：%s" % bool(ended and (ended[-1].get("data") or {}).get("minutes")))
            push_ok = all(e in events for e in ("meeting_started", "answer", "meeting_ended")) and bool(ended)

        ok = s["state"] == "idle" and bool(m.get("conclusions")) and push_ok
        print("\n结果：%s" % ("通过" if ok else "有问题，看上面"))
        return 0 if ok else 2
    finally:
        try:
            proc.kill()
        except Exception:
            pass
        srv.shutdown()
        errs = [l for l in log_lines if "Traceback" in l or "Error" in l or "WARNING" in l or "warning" in l]
        if errs:
            print("\n后端日志里的告警/错误（前 15 行）：\n" + "\n".join(errs[:15]))


if __name__ == "__main__":
    sys.exit(main())
