"""不需要机器人、不需要 SDK、不需要任何 key：python run_local.py
终端里打字当作说话，或者在看板页面底部的输入框里打字。"""
import asyncio
from main import run

asyncio.run(run(None))
