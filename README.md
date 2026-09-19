# 会议主持机器人

放在会议室里的主持人：会前读资料，会中转写、计时、管跑题，被叫到名字才回答，散会前拍背确认待办，下次开场先追上次的待办。
产品形式：Web 看板（局域网）加 WatcheRobot 桌面机器人。背景见 `docs/产品文档.md`，直观印象打开 `docs/产品蓝图.html`。

## 现在就能跑（不需要机器人和任何 key）

```
pip install -r requirements.txt
python run_local.py
```

打开终端里打印的看板地址。在页面底部输入框依次输入：

1. `主持人，开始供应商报价的会议`
2. `主持人，记下这个重点：B 家排除`
3. `张三，周五前拿到 A 家的正式报价`
4. `主持人，会议结束`，然后点“拍背”

整条链路现在用的是假语音、假机器人、假大脑。每个人把自己的假模块换成真的。

## 接真机器人

```
watcherobot robot pair <配对码>
watcherobot app run .
```

在 `.env` 里用 `USE_FAKE_SPEECH=1` 这类开关单独切换某个模块的真假。填了 `LLM_KEY` 自动用真大脑。

## 分工

| 人 | 目录 | 要做的 |
| --- | --- | --- |
| A 集成 | `core/` `robot_io/` `main.py` `app.py` `contracts.py` | 状态机调优，`robot_io/cues.py` 对照真机核对行为 ID 和灯效，拿着机器人联调 |
| B 语音 | `speech/` | `providers.py` 接 ASR 和 TTS，`segmenter.py` 调阈值，`commands.py` 补指令说法 |
| C 大脑 | `brain/` | `.env` 配 LLM，`prompts.py` 调提示词，联网搜索参数，长转写压缩 |
| D 页面和演示 | `web/static/` `demo/` | 三个页面做好看，二维码，演示资料和台词，彩排 |

## 数据流

```
speech --一句话--> core（状态机） --cue/say--> robot_io / speech
                     |--调用--> brain（资料 + 转写 + 历史 -> 回答、跑题、纪要）
                     |--快照--> web（/ws 推送看板）
```

## 时间点

0:20 每人跑通 run_local · 1:00 第一次联调 · 1:45 第二次联调（真模块） · 2:30 冻结 · 之后只彩排
