"""SDK 入口。必须用 `watcherobot app run` 启动，不要直接 python app.py。"""
import asyncio

from watcherobot.application import ApplicationContext

from main import run


async def main() -> None:
    async with ApplicationContext.from_environment() as app:
        app.logger.info("capabilities: %s", app.robot.capabilities)
        connected = app.robot.supports("behavior")
        if not connected:
            app.logger.info("没有连接机器人，全部使用假模块。先执行 watcherobot robot setup。")
        await run(app if connected else None)


asyncio.run(main())
