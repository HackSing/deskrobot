# 演示对接方案，mock 版

更新日期：2026-09-19。距离演示一小时时定的方案，以这份为准，`docs/H5对接方案_MVP.md` 和 `docs/接口说明.md` 留作演示后的完整版。

原则：只有会中问答是真 LLM，其余全部是脚本和预置数据。三方只靠现有契约对接，不新增接口。

## 1. 演示流程

| 步 | 用户做什么 | 硬件侧 | 后端 | H5 |
| --- | --- | --- | --- | --- |
| 1 | 扫码打开 H5，点"上传资料" | 无 | 启动时已预置资料和会前准备 | 假上传，只显示文件名；展示后端已就绪的资料 |
| 2 | 说"小登，开始会议" | 识别整句，回调后端；播开场白 | 进 meeting，固定开场白，随后按固定间隔把 mock 会议记录灌进转写 | 自动切会中看板，转写一条条出现 |
| 3 | 说"小登，<问题>"，可多次追问 | 识别整句，回调；播"我看一下"，再播回答 | 真 LLM，基于资料、完整 mock 记录、本场对话历史，两句话以内 | 看板显示最近问答 |
| 4 | 说"小登，会议结束" | 识别整句，回调；播固定结束语 | 固定回复，加载 mock 纪要，不做拍背确认，落库并广播 | 自动切纪要页 |
| 5 | 在手机上看纪要 | 无 | 无 | 显示结论、待办、未决、重点 |

## 2. 硬件侧需要的

契约就是 `contracts.py` 里的 SpeechIO 和 RobotIO，签名不变。演示只用到其中一部分。

**必须实现**

| 接口 | 要求 |
| --- | --- |
| `SpeechIO.run(on_utterance)` | 持续录音、切句、ASR，每句回调一次 `Utterance(text, ts)`。text 是整句原文，含"小登"，不要自己切掉唤醒词 |
| `SpeechIO.say(text)` | TTS 并播放，播完才返回。播放期间不回调 `on_utterance` |
| `RobotIO.cue(name)` | 演示只会收到 standby、meeting_start、idle、thinking、speaking 五个，其他名字可以空实现 |

**可以空实现**：`set_progress`、`run_inputs`、`face_tracking`。演示不用拍背和跟随。

**唤醒词和指令**，每次都要叫名字，不叫名字的话后端只当作普通发言，不会触发任何动作

| 用户说 | 后端识别为 | 机器人回复 |
| --- | --- | --- |
| 小登，开始会议 | start | 固定开场白，由后端拼好传给 say |
| 小登，资料里 A 家的交期是多少 | ask | 先"我看一下。"，再真实回答，两句话以内，带来源 |
| 小登，那 C 家呢 | ask，后端靠对话历史接上文 | 同上 |
| 小登，会议结束 | end | "好的，会议结束。会议纪要马上推送到大家的手机。" |

**一次问答的时序**：回调 on_utterance，后端 cue(thinking)，say("我看一下。")，LLM 两到六秒，cue(speaking)，say(回答)，cue(idle)。两次 say 之间硬件不用做任何事。

**备用通道**，硬件代码跑在独立进程时用：识别出的整句 `POST /api/debug/say`，body `{"text": "小登，开始会议"}`；订阅 `ws://IP:8766/ws`，快照里 `say_id` 变化时把 `last_said` 送 TTS，`cue` 字段做表情。

**没有硬件时**：桌面看板底部的调试框，或 H5 加 `?debug=1`，输入同样的句子，整条链路照跑。

## 3. H5 需要的

页面地址 `http://局域网IP:8766/h5`，后端启动时会把地址打印在终端，用任意二维码工具生成二维码即可，不依赖代码。

数据只有一条快照。`ws://IP:8766/ws` 连上先收一条完整快照，之后每次变化都收一条完整快照，不是增量。刷新用 `GET /api/state`。不新增任何接口。

**视图规则**，页面不维护流程状态

| 条件 | 视图 |
| --- | --- |
| state 为 meeting 或 confirming | 会中看板 |
| 否则 minutes 非空 | 纪要页 |
| 否则 | 准备页 |

**用到的字段**，全部已存在

| 字段 | 视图 | 说明 |
| --- | --- | --- |
| `state` | 全部 | idle、meeting、confirming |
| `materials` | 准备页 | 后端预置的资料文件名列表，显示为"已就绪" |
| `project` | 会中 | 项目名 |
| `agenda`、`current_item` | 会中 | 当前议题取 agenda[current_item].title |
| `elapsed`、`total` | 会中 | 秒，做 mm:ss 和进度条 |
| `transcript` | 会中 | 每项 text，显示最近 6 条 |
| `marks` | 会中 | 已记重点 |
| `last_answer` | 会中 | question、text、source |
| `last_said` | 会中 | 小登刚说 |
| `minutes` | 纪要 | conclusions、todos 每项 owner、content、due、confirmed，open_questions、highlights |

后端会多给 `cue`、`say_id`、`demo` 三个字段，H5 忽略。

**假上传**：选文件后只在界面显示"已上传 文件名"，不发请求。资料真正的来源是后端预置的 `demo/演示资料_供应商对比表.md`。

`source` 标签：materials 会议资料、transcript 本场转写、history 历史纪要、web 联网、none 没找到。

## 4. 后端预置的内容

| 内容 | 文件 | 说明 |
| --- | --- | --- |
| 会前准备 | `demo/seed.py` 的 seed_demo | 项目"供应商报价"，两个议题各 10 分钟，参会人张三李四王五，资料一份 |
| 资料 | `demo/演示资料_供应商对比表.md` | A、B、C 三家的单价、交期、起订量 |
| mock 会议记录 | `demo/mock_transcript.json` | 二三十条，会中按间隔灌进转写；问答时 LLM 看到的是全部 |
| mock 纪要 | `demo/mock_minutes.json` | 结束时直接加载；设 MINUTES_FROM_LLM=1 改为真 LLM 生成 |

环境变量，写在 `.env`：

```
ROBOT_NAME=小登
DEFAULT_PROJECT=供应商报价
DEMO_MODE=1
MOCK_DRIP_SECONDS=4
ASK_FILLER=我看一下。
END_TEXT=好的，会议结束。会议纪要马上推送到大家的手机。
CONFIRM_TODOS=0
MINUTES_FROM_LLM=0
LLM_URL=https://api.deepseek.com/chat/completions
LLM_KEY=向大脑负责人要，不进仓库
LLM_MODEL=deepseek-flash
LLM_EXTRA={"thinking":{"type":"disabled"},"max_tokens":400}
```

LLM 用 DeepSeek 的 OpenAI 兼容端点，已实测可用。deepseek-flash 是推理模型，LLM_EXTRA 里关闭思考是必须的，否则推理内容会把 max_tokens 吃光、正文返回空串；关闭后一次问答约 1 秒。LLM_KEY 不填就自动用假大脑，问答退化为关键词匹配，其余流程照跑。

## 5. 联调步骤

1. 后端 `python run_local.py`，终端打印看板地址和 H5 地址。所有设备连同一个 Wi-Fi。
2. 手机打开 H5，看到准备页和已就绪的资料。
3. 桌面看板调试框输入"小登，开始会议"，手机应切到会中看板，转写开始一条条出现。
4. 输入"小登，资料里 A 家和 C 家的交期分别是多少"，再输入"小登，那 B 家呢"，看回答是否接上。
5. 输入"小登，会议结束"，手机应切到纪要页。
6. 以上全通后再换真硬件走一遍，把调试框输入换成对着机器人说。

## 6. 保底

- 硬件没通：用调试框输入代替说话，机器人不出声，H5 照常演。
- LLM 没通或太慢：LLM 三项留空用假大脑；或演示时只问资料里有的数字，假大脑能答。
- H5 没通：桌面看板本来就能显示全部字段，投到大屏。
- 演示重来：重启后端即可，会前准备和资料每次启动都会重新预置。
