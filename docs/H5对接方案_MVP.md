# H5 对接方案 MVP

更新日期：2026-09-19。给前端 H5 用，先按这份做。目标：一台手机发起，两台手机扫码加入，会中看板，散会后纪要自动推到每台手机。只保留跑通这条链路的字段和接口，完整版见 `docs/接口说明.md`。

## 1. 范围

做：

- 发起会议，发起后出二维码
- 扫码加入的门禁：没发起不能进，二维码换场失效
- 发起人上传资料，复用现有接口
- 发起人点"开始会议"，作为语音指令的备份
- 会中看板
- 散会后所有连着的手机自动切到纪要页，本人待办高亮

不做，留到完整版：

- 发起人令牌和参与人 ID，局域网演示不做鉴权
- 作废房间，演示重来直接重启后端
- 待办完成勾选
- 多来源 sources、机器人当前反馈 cue、正在确认第几条 confirming_index、服务器时间 server_ts
- 加入者时间戳

## 2. 数据流

页面只依赖一条快照。WebSocket `/ws` 连上先收一条完整快照，之后状态一变就再收一条完整快照，不是增量。刷新页面用 `GET /api/state` 拿同样的东西。写操作只有四个 POST 加一个上传。

约定：所有接口返回 JSON；出错返回 4xx 和 `{"error": "原因"}`。

## 3. 快照里必需的字段

| 字段 | 类型 | 用在哪 | 后端状态 |
| --- | --- | --- | --- |
| `state` | string | 全部页面。`idle` 空闲、`meeting` 会中、`confirming` 确认待办中，后两个都显示会中看板 | 已有 |
| `project` | string 或 null | 会中看板标题 | 已有 |
| `agenda` | 列表，每项 `title`、`minutes` | 会中看板显示当前议题 | 已有 |
| `current_item` | int | 当前议题在 agenda 里的下标 | 已有 |
| `elapsed`、`total` | int 秒 | 计时和进度条 | 已有 |
| `transcript` | 列表，每项 `text` | 会中看板，最近 50 句，MVP 只显示最后 5 句 | 已有 |
| `marks` | string 列表 | 会中看板已记重点 | 已有 |
| `last_answer` | 对象或 null，`question`、`text`、`source` | 会中看板最近问答 | 已有 |
| `last_said` | string | 会中看板"小登刚说" | 已有 |
| `minutes` | 对象或 null | 纪要页。`conclusions`、`open_questions`、`highlights` 都是 string 列表；`todos` 每项用 `owner`、`content`、`due`、`confirmed` | 已有 |
| `session` | 对象或 null | 见下 | 待加 |

`session` 的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | `none` 没有房间、`open` 已发起可扫码、`in_meeting` 会中、`ended` 已结束 |
| `session_id` | string | 房间 ID，二维码里带的就是它 |
| `project` | string | 项目名 |
| `join_url` | string | 完整加入链接，直接拿来生成二维码 |
| `participants` | string 列表 | 发起表单里填的参会人，加入页做名字候选 |
| `joined` | string 列表 | 已扫码加入的名字，发起页显示名单 |

`last_answer.source` 五种取值和中文标签：`materials` 会议资料、`transcript` 本场转写、`history` 历史纪要、`web` 联网、`none` 没找到。

快照里其他字段 MVP 忽略：`robot_name`、`meeting_id`、`materials`、`transcript[].ts`、`todos` 的其他字段。

## 4. 接口

新增四个，都不鉴权：

| 方法 | 路径 | 请求 | 响应 |
| --- | --- | --- | --- |
| POST | `/api/session` | `project` string，`agenda` 列表每项 `title`、`minutes`，`participants` string 列表，`background` string | `session_id`，`join_url`。已有 open 或 in_meeting 的房间返回 409 |
| GET | `/api/session` | 无 | 与快照里的 `session` 相同，没有房间时 `status` 为 `none` |
| POST | `/api/session/join` | `session_id` 来自 URL 参数 s，`name` string | `ok`，`name`。没有房间或房间已结束返回 403 且 error 为"会议还没发起"；`session_id` 不是当前房间返回 403 且 error 为"二维码已失效" |
| POST | `/api/session/start` | 无 | `ok`。房间不是 open 返回 409 |

复用现有的：

| 方法 | 路径 | 请求 | 响应 |
| --- | --- | --- | --- |
| GET | `/api/state` | 无 | 完整快照 |
| WS | `/ws` | 无 | 完整快照，每次变化推一条 |
| POST | `/api/materials/{project}` | multipart 字段 `file`，project 用发起时填的项目名 | `ok`，`filename`，`chars`。不支持的类型返回 400 |
| POST | `/api/debug/say` | `text` string | `ok`。联调时模拟有人说话，不用机器人 |

`join_url` 形如 `http://192.168.1.8:8766/h5?s=20260919-1530-a1b2`，后端把 `/h5` 映射到 `web/static/h5.html`，前端从 URL 参数 s 取 `session_id`。

## 5. 页面与状态

单文件 `web/static/h5.html`，hash 路由四个视图：

| 视图 | 路由 | 内容 |
| --- | --- | --- |
| 发起页 | `#host` | 表单：项目、议程每行"标题，分钟"、参会人、背景；发起按钮。发起后变成二维码、已加入名单、上传资料、开始会议 |
| 加入页 | `#join` | 从 URL 参数 s 读房间 ID；房间不可加入时显示提示；可加入时显示名字候选加自由输入，加入后进等待页 |
| 会中看板 | `#live` | 计时、进度条、当前议题、最近五句转写、已记重点、最近问答、小登刚说 |
| 纪要页 | `#minutes` | 结论、待办、未决问题、重点；`owner` 等于本人名字的待办高亮，`confirmed` 为真显示"已拍背确认" |

视图切换全部由快照驱动，页面不自己维护流程状态：

| `session.status` | `state` | 发起人 | 参与人 |
| --- | --- | --- | --- |
| none | idle | 发起表单 | "会议还没发起" |
| open | idle | 二维码、名单、上传、开始按钮 | 加入页；加入后显示"已加入，等待开始" |
| in_meeting | meeting 或 confirming | 会中看板 | 会中看板 |
| ended | idle | 纪要页 | 纪要页 |

本地存储只存两个键：`name` 本人名字，`session_id` 加入时的房间。快照里的 `session.session_id` 与本地不一致就清掉，回到加入页。

二维码前端生成，把一个 JS 二维码库放进 `web/static/vendor/`，不依赖外网。

## 6. 样例快照

后端房间接口做好之前，前端用这几份静态 JSON 开发。字段与真实后端一致。

已发起、等人扫码：

```json
{"state":"idle","project":null,"agenda":[],"current_item":0,"elapsed":0,"total":0,
 "transcript":[],"marks":[],"last_answer":null,"last_said":"","minutes":null,
 "session":{"status":"open","session_id":"20260919-1530-a1b2","project":"供应商报价",
  "join_url":"http://192.168.1.8:8766/h5?s=20260919-1530-a1b2",
  "participants":["张三","李四","王五"],"joined":["张三"]}}
```

会中：

```json
{"state":"meeting","project":"供应商报价",
 "agenda":[{"title":"对比三家供应商","minutes":6},{"title":"定下一步动作","minutes":4}],
 "current_item":0,"elapsed":95,"total":600,
 "transcript":[{"text":"B 家最便宜，但起订量要五千。"},{"text":"小登，记下这个重点：B 家因起订量排除"}],
 "marks":["B 家因起订量排除"],
 "last_answer":{"question":"资料里 A 家和 C 家的交期分别是多少","text":"A 家交期 45 天，C 家 30 天。","source":"materials"},
 "last_said":"A 家交期 45 天，C 家 30 天。来源：会议资料。","minutes":null,
 "session":{"status":"in_meeting","session_id":"20260919-1530-a1b2","project":"供应商报价",
  "join_url":"http://192.168.1.8:8766/h5?s=20260919-1530-a1b2",
  "participants":["张三","李四","王五"],"joined":["张三","李四","王五"]}}
```

已结束、纪要推送：

```json
{"state":"idle","project":"供应商报价",
 "agenda":[{"title":"对比三家供应商","minutes":6},{"title":"定下一步动作","minutes":4}],
 "current_item":1,"elapsed":0,"total":600,"transcript":[],"marks":["B 家因起订量排除"],
 "last_answer":null,"last_said":"2 条结论，1 条待办，已保存。",
 "minutes":{"conclusions":["B 家因起订量排除","优先谈 A 家"],
  "todos":[{"owner":"张三","content":"拿到 A 家的正式报价","due":"周五前","confirmed":true}],
  "open_questions":["C 家芯片是否停产"],"highlights":["B 家因起订量排除"]},
 "session":{"status":"ended","session_id":"20260919-1530-a1b2","project":"供应商报价",
  "join_url":"","participants":["张三","李四","王五"],"joined":["张三","李四","王五"]}}
```

## 7. 联调步骤

1. 后端 `python run_local.py`，终端会打印局域网地址。手机和电脑连同一个 Wi-Fi。
2. 手机 A 打开 `/h5#host`，填表发起，出二维码。
3. 手机 B 扫码，选名字加入。手机 A 上名单应出现 B 的名字。
4. 手机 A 点开始会议，或在桌面看板调试框输入"小登，开始供应商报价的会议"。两台手机都应切到会中看板。
5. 桌面看板调试框依次输入台词，两台手机的转写和重点应同步刷新。
6. 输入"小登，会议结束"，点拍背。两台手机都应自动切到纪要页，各自名下的待办高亮。

## 8. 大脑侧要做的

给后端自己看，全部在 `web/server.py`，估计 80 行：

- 房间放内存字典：`status`、`session_id`、`project`、`participants`、`joined`。
- 四个接口。发起时内部调现有的保存会前准备；加入时把名字追加进会前准备的参会人并保存，大脑生成待办时才能对上名字；开始时用 `ROBOT_NAME` 拼一句开会指令送进状态机。
- `/api/state` 和 `/ws` 发出去之前把 `session` 合并进快照。
- 用 `orch.bus.subscribe` 订阅快照：state 变 meeting 时房间置 in_meeting；state 回 idle 且 minutes 非空且房间是 in_meeting 时置 ended，并清空 `join_url`。
- `/h5` 路由返回 `web/static/h5.html`。
- `join_url` 用现有的 `lan_ip()` 和 `WEB_PORT` 拼。
