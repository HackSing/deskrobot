"""提示词。C 负责调。"""

PARSE_OPENING = """从这句会议开场白里提取信息，只输出 JSON：
{"project": 项目名或 null, "total_minutes": 总时长分钟数或 null, "agenda_count": 议题数或 null}
开场白：{text}"""

ANSWER = """你是会议室里的主持人机器人。有人在会上问了你一个问题。
按下面的顺序找答案，找到就停：1 会议资料，2 本场转写，3 历史纪要。都没有时 source 填 "none"。
规则：回答不超过两句话，口语，不要列表。不要编造。引用资料时说出文件名和页码（如果有）。
只输出 JSON：{"text": "回答", "source": "materials" | "transcript" | "history" | "none"}

【会议背景】{background}
【会议资料】{materials}
【历史纪要】{history}
【本场转写】{transcript}
【问题】{question}"""

ANSWER_WEB = """用联网搜索回答这个会议上的问题。不超过两句话，口语，最后说出信息来自哪个网站或机构。查不到就直说查不到。
最近的讨论：{recent}
问题：{question}"""

OFF_TOPIC = """会议议程：{agenda}
当前议题：{current}
最近 30 秒的发言：{recent}
这些发言是否明显偏离了会议议程（比如聊吃饭、八卦、无关项目）？与任一议题相关都不算跑题。拿不准就算没跑题。
只输出 JSON：{"off_topic": true 或 false}"""

MINUTES = """根据会议转写生成纪要。参会人：{participants}。待办的负责人必须是参会人名单里的人或转写里出现的名字。
只输出 JSON：
{"conclusions": ["结论"], "todos": [{"owner": "负责人", "content": "做什么", "due": "什么时候前，没有就空字符串"}],
 "open_questions": ["没定下来的问题"], "highlights": ["重点"]}
用户标记的重点（必须收进 highlights）：{marks}
【会议资料】{materials}
【转写】{transcript}"""
