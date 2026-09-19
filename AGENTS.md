# 给 AI 编码助手的规则（每个人先让自己的 AI 读这个文件和 contracts.py）

1. 只修改分给你的目录，见 README 的分工表。不要动别人的目录。
2. 不要修改 `contracts.py`、`main.py`、`app.py`、`app.json`。需要改就告诉负责人 A。
3. 模块之间只通过 `contracts.py` 里的数据类和接口交互，不要互相 import 内部实现。
4. WatcheRobot SDK 的调用都是阻塞的，必须包在 `asyncio.to_thread` 里。
5. 新增第三方依赖：告诉 A，由 A 同时写进 `app.json` 和 `requirements.txt`。
6. key 只放 `.env`，不要写进代码，不要提交。
7. 改完先跑 `python -m pytest -q` 和 `python run_local.py`，能跑再提交。
8. 小步提交，推送前 `git pull --rebase`。只用 main 分支。
