# WatcheRobot SDK 开发指南

# 准备环境

要求 Python 3\.10～3\.12。普通 Application 开发者不需要克隆 SDK 仓库，直接从 PyPI 安装。当前稳定版是 [`watcherobot 0.1.1`](https://pypi.org/project/watcherobot/0.1.1/)；需要可复现环境时使用 `python -m pip install "watcherobot==0.1.1"`。

```PowerShell
#创建conda环境
conda create -n watcherobot-source python=3.11 -y
conda activate watcherobot-source

#安装环境，没有conda也可直接在python环境下执行安装
python -m pip install watcherobot
watcherobot --version

#查看
watcherobot --help
```

如有疑问，小伙伴可以看详细的安装配置教程：[安装 WatcheRobot Python SDK](https://mcnsslrwxv50.feishu.cn/wiki/RWEfwafx4iud3IkVXWdcAgKyn9c)

**SDK源代码仓库**：https://github\.com/orulink\-ai/WatcheRobot\_python\_sdk\.git

# 启动守护进程

启动守护进程（负责设备的连接，管理应用等）

```PowerShell
# 启动
watcherobot daemon start

# 查看运行状态
watcherobot daemon status
```

# 第一步连接设备

## 蓝牙配置网络

首先我们先要给设备配置wifi网络，是我们使用sdk连接设备的前提

设备中进入wifi配置页面

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MDRjNWZhOWQwODFiMWM2NzY2OGVmZDI5NDEyMjNmYTJfM2VhZDEwZTJmNDJkMDBkNWNlYjIwNjdlNjBmODJlYmFfSUQ6NzY4Njc2NTUwNjUwNzE4MTI2NV8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=M2ZkYTAzZTQ5YzQ2M2Q0ZDMwZjRmYTI3MTk5YWY5MDdfMTcxNGQ3ZGJkZGZjNTA0YTU3MzkxMjZkMWY5YmI0YWZfSUQ6NzY4Njc2NTU3MDMzOTM2MDAzNl8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NjAwYzg3N2U5NDNhMDFmN2U3YmMxNTEwY2Q4MmRjZWZfZmU4ODI4YmUwNzA0MjJjZTJjOGI1ODk5ZTYxNTlkMDhfSUQ6NzY4Njc2NTYxNjY4Njk0MzE3NF8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

### 方式一、命令行配置网络（确保当前设备有蓝牙）

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmY2OGYxYTFlYmEyMDIzMDJlZWJhMjQwZDY0ZTM3OThfYTc0MGNiNTdkNDBhODMyNjkyMWVkOWVjODAwNGNmMDVfSUQ6NzY4Njc2NzE1NTI1OTQ5MzMwOF8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

```PowerShell
# 启动配网
watcherobot robot setup
```

**直接回车**


![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NTc3ZWFjMjNhMWVkYjZlNTU0NThkMWFiMjk0YTgwM2FfODZhOWEwMWZlYTliNTMzMjdhMzUxYTkyMThhNmU1NTlfSUQ6NzY4Njc2OTQyNjE2NzE3MjMwMV8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

**输入wifi名称和密码**

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=NDg5ODhlNDFkOTZiNWEyMDM5ZmUyOTI2ZmE3YzRjOTdfZTEzNjUyZjU0MmVjM2RjNGVmNThlY2I4NDk5MGQ5Y2ZfSUQ6NzY4Njc2OTc3NTY2MjQxODg5NF8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

### 方式二、使用app进行网络配置

下载我们的手机应用app，即可进行可视化配置设备的网络

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=ZmY5YzY4NDhmZjk0N2M0YmY0OGEwNjZkNDkwN2JjZjJfZjVjZGI5NGQ3NDc4NmJhYjk0N2ZmZDI3NDk1OWYwMGZfSUQ6NzY4Njc2ODI2NTc1MDMwMTk2Nl8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmM3NDliMDg4MjIzZGM2NmYxMjQzODhjOTI0N2M1MTlfOWEzNjIxMWZiZTE4ZDVhNjRjY2QyNjhiMTc2OThhZTZfSUQ6NzY4Njc2ODI5MzIwNjE5OTIyNl8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmFkYTFhYzM0MzE0YjRkYjg0YzRmNjNiZWRhNjFhMDRfMDllMTdhYThjZTFjMjVjNTEyMDZlZTcxMmFlOGFiNzZfSUQ6NzY4Njc2ODMyODAyMzQ5MzkwNl8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MTk1NWNiZjFiMTMwMzg0Nzg5OTc3NjIwNjhlMGQ4ODVfMDljY2NmZTdmYzM5M2IxYTZlNjVjZWU2NjQ5NDUyZTBfSUQ6NzY4Njc2ODM1MjczOTY3NTM0OV8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

## 连接设备

确保设备和电脑处于同一个局域网后，在设备进入连接模式

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MTg3ZTkxNTEwY2NjODFmNTExYjEwNDY1ZWQ1YTAzMDNfZDlhNmQ5NWZjMzdhZWE1YTUxOGI4YjgwNzg4ZjcxYTVfSUQ6NzY4Njc3MDYzMTY3Njg3Mzk5OF8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MmNjNjNiOTVjYjQ3NGIxOTY1YjNhYzJmYjBiZDVkYjNfOGY0ODI5MTNjODhjZTExMDdjMTkxNDNmNDQzN2ZlZDlfSUQ6NzY4Njc3MDY1NzIwNzYzNTEyNV8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

会显示**配对码**（例如：667377）

```PowerShell
# 启动配网
watcherobot robot pair <配对码>
```

![Image](https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/authcode/?code=MWVkZWM1ODEwOTNiYWM4ZTI5NzBmNTEwZWZkN2EyYWJfYTI1MjRlMDZiZTBhNmNjNmRmYzk1ZGU1MGY3ZDdmZTFfSUQ6NzY4Njc3MTAzODMxMDU1MDc3MF8xNzg5Nzk4NTI1OjE3ODk4ODQ5MjVfVjM)

这样就连接成功啦！！



# 运行第一个机器人应用

## 创建项目

```PowerShell
# 快速创建一个名为 my_app 的 Application 项目
watcherobot app init my_app
```

**两条命令作用相同，都会创建一个可直接运行的 Application 项目。**第一条使用自动生成的默认信息；第二条在创建时自定义应用 ID、名称、作者和说明。

```PowerShell
# 创建项目，并在创建时指定 Application 的展示和发布信息
watcherobot app init my_app --id com.example.my_app --name "My Robot App" --author "Your Team" --description "My first WatcheRobot Application"
```

应用信息创建后仍可在 `app.json` 中修改。目标目录必须不存在。

## 创建后会得到什么

```Plain Text
my_app/
├── app.json       Application 名称、版本和依赖
├── app.py         固定的程序入口
├── README.md      当前 Application 的说明
├── icon.svg       商店和桌面端显示的图标
└── .gitignore     不应提交到 Git 的文件
```

`watcherobot app run` 会读取 `app.json`，确认 SDK 版本和依赖，再通过 Runtime 启动固定入口 `app.py`。因此不要直接执行 `python app.py`：直接运行时缺少 Runtime 注入的设备连接和授权信息。

## app\.json 是什么

```JSON
{
  "schema_version": 1,
  "id": "local.my_app",
  "name": "My App",
  "version": "0.1.0",
  "requires_watcherobot": ">=0.1.1,<0.2",
  "dependencies": [],
  "description": "My App WatcheRobot Application.",
  "author": "Local Developer",
  "icon": "icon.svg"
}
```

|字段|作用|
|---|---|
|`id`|全局唯一 ID，建议使用反向域名，例如 `com.company.app_name`。|
|`name`|展示给用户看的名称。|
|`version`|Application 自身版本，使用三段式语义化版本。|
|`requires_watcherobot`|允许使用的 SDK 版本范围，初始化时自动生成。|
|`dependencies`|额外 Python 依赖，例如 `requests>=2.32,<3`。|
|`description` / `author`|本地开发会生成默认值；提交商店前应替换为真实应用介绍和作者。|
|`icon`|项目内的图标文件路径。|

## 编写第一个程序

初始化器已经把下面的 Hello World 代码生成到 `my_app/app.py`，第一次运行不需要手工修改：

```Python
import asyncio

from watcherobot.application import ApplicationContext


async def main() -> None:
    async with ApplicationContext.from_environment() as app:
        app.logger.info("Hello, WatcheRobot! Your first Application worked.")
        if not app.robot.supports("behavior"):
            app.logger.info(
                "No compatible robot is connected, so the happy behavior was "
                "skipped. Run 'watcherobot robot setup' to connect one."
            )
            return

        job = await asyncio.to_thread(
            app.robot.behavior.play,
            "happy",
            repeat=1,
        )
        await asyncio.to_thread(job.wait, 20.0)
        app.logger.info("The robot played the happy behavior.")


asyncio.run(main())
```

**`ApplicationContext.from_environment()`****：**读取 Runtime 注入的 Application ID、Desktop channel 和 Device channel。它只能在 `watcherobot app run` 或 Desktop 管理的 Application 进程中使用。

**`async with`****：**进入时连接 Runtime，退出时关闭 RTC、麦克风、相机等 SDK 资源，避免资源泄漏。

**`app.robot.supports()`****：**检查当前固件是否声明某项能力。这样旧固件或不同硬件版本不会因为缺少能力直接报错。

**`asyncio.to_thread()`****：**机器人高级 API 是阻塞调用，把它放到工作线程可以避免阻塞 Application 的异步事件循环。

**`Job.wait()`****：**等待设备上报行为完成，而不是发送命令后立即退出 Application。

## 检查并运行

```PowerShell
cd my_app
watcherobot app run

# 可选：发布前或 CI 中执行完整检查
watcherobot app check .
```

`app run` 会自动启动或复用 Runtime，不需要先执行 `daemon start`。未连接机器人时，CLI 会提示执行 `watcherobot robot setup`，Application 仍会输出 `Hello, WatcheRobot!` 并以退出码 `0` 正常结束；连接兼容机器人后，还会播放一次 `happy`。这两个结果分别验证 Application 生命周期和真实设备链路。

## 检查和测试有什么区别

|命令|作用|
|---|---|
|`watcherobot app check .`|检查 Application 结构、app\.json、入口、依赖和 SDK 版本；它不会运行机器人，也不会执行你的单元测试。|
|`python -m pytest`|运行你或 SDK 仓库编写的自动化测试。app init 默认不生成 tests 目录；需要测试业务逻辑时，由开发者创建 tests/。|
|`python -m mypy src/watcherobot`|这是 SDK 仓库维护者检查 SDK 类型的命令，普通 Application 不需要照搬这个路径。|

第一次开发 Application 时，先直接执行 `watcherobot app run` 获得真机反馈；发布前或 CI 中再运行 `app check`。业务逻辑开始变复杂后，为不依赖硬件的判断逻辑添加 pytest 测试；动画、摄像头、麦克风和 RTC 仍需真机端到端验证。

## 原子能力一览

- **运动：**控制水平、俯仰角度，或播放已有舵机动作。

- **行为：**播放官方表情、作品表情和设备动画，也可动态调整眼睛、视线、颜色、眨眼和配饰。

- **音频播放：**通过机器人扬声器播放音频文件或 PCM 音频，并可停止播放。

- **麦克风：**实时接收麦克风音频，或录制指定时长的 PCM 音频。

- **摄像头与录制：**拍摄照片，录制视频、音频或带声音的视频。

- **灯光：**设置灯光区域、颜色和亮度，播放呼吸等灯效，或关闭灯光。

- **视觉：**查询和选择设备模型，运行识别或检测，并获取结果和预览画面。

- **人脸跟随：**启动或停止设备端人脸跟随，并获取带人脸框的预览画面。

- **设备输入：**接收背部触摸、屏幕点击和滚轮旋转事件。

- **自定义 UI：**Application 可以创建自己的桌面窗口或网页界面，用于按钮控制、状态展示、参数输入和结果预览。

实际可用能力取决于设备固件、已安装资源和 `app.robot.capabilities`。语音识别、图像识别和 AI 对话需要在这些原子能力上组合模型或服务实现。

# 接下来做什么

- 想控制动画、云台、灯效、拍照或麦克风：阅读“机器人能力与 Python API 指南”。

- 准备做实时音频或视频：先阅读“音视频能力边界与场景设计”，不要从“接口存在”推断组合一定可用。

- 准备发布给其他用户：阅读“Application 发布与上架指南”。

[https://mcnsslrwxv50.feishu.cn/wiki/Bf67wIygni6HkNkd9JXcVpItnLd]()

[https://mcnsslrwxv50.feishu.cn/wiki/ZrKfwDPYTij9I0kWKoocMNbMnYd]()



