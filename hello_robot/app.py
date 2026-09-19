"""WatcheRobot Application entrypoint."""

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
