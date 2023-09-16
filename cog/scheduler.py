import asyncio
import logging
from typing import Coroutine

from discord import utils
from discord.ext import commands

from cog.classes.scheduler_task import SchedulerTask

# TODO: Make this a util function that will take the file name from cog.


def set_logger(logger: logging.Logger) -> None:
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="scheduler.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class SchedulerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = logging.getLogger("scheduler")
        set_logger(self.logger)
        self.current_schedule = None
        self.schedules: list[SchedulerTask] = []
        # A "boolean" that can set/get if there is a schedule, waited if there is none.
        self.has_schedule = asyncio.Event()

        self.task = bot.loop.create_task(self.scheduler())
        self.logger.info("Scheduler Cog has been initialised.")

    async def scheduler(self) -> None:
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.current_schedule = await self.get_oldest_schedule()
            print(self.current_schedule)
            self.logger.info(
                f"New task waiting to execute at {self.current_schedule.expires_at.strftime('%d/%m/%Y-%H:%M:%S')}"
            )
            await utils.sleep_until(self.current_schedule.expires_at)
            if isinstance(self.current_schedule.task, Coroutine):
                await self.current_schedule.task()
                self.logger.info("Asynchronous task has been executed")
            else:
                self.current_schedule.task()
                self.logger.info("Synchronous task has been executed")
            self.remove_schedule(self.current_schedule)

    async def get_oldest_schedule(self):
        if len(self.schedules) == 0:
            # Will block until self.has_schedule gets set.
            self.logger.info("Scheduler has now paused.")
            await self.has_schedule.wait()

        # Return the task that's closest to current time.
        return min(self.schedules, key=lambda i: i.expires_at)

    def schedule_item(self, item: SchedulerTask) -> None:
        if len(self.schedules) == 0:
            self.schedules.append(item)
            # Resume the function that gets blocked by self.has_schedule event
            self.has_schedule.set()
            self.logger.info("Scheduler has now resumed as an item has been added.")
            return

        self.schedules.append(item)
        self.logger.info("Item has been added.")

        if self.current_schedule is not None and item < self.current_schedule:
            # Restart scheduler if theres a task with a closer expiry time.
            self.task.cancel()
            self.logger.info(f"Current task has been canceled, restarting schduler.")
            self.task = self.bot.loop.create_task(self.scheduler())
            self.logger.info("Scheduler has restarted.")

    def remove_schedule(self, item: SchedulerTask) -> None:
        try:
            self.schedules.remove(item)
        except ValueError:
            pass
        else:
            if len(self.schedules) == 0:
                # Blocks the function governed by the self.has_schedule event
                self.logger.info("Scheduler is now clearing event.")
                self.has_schedule.clear()

    async def cog_load(self):
        await super().cog_load()

    async def cog_unload(self):
        await self.task.cancel()
        self.logger.info("Scheduler Cog is unloading, current task cancelled.")
        await super().cog_unload()


async def setup(bot):
    await bot.add_cog(SchedulerCog(bot))


async def teardown(bot):
    await bot.remove_cog(SchedulerCog(bot))
