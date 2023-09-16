from datetime import datetime, timedelta
from functools import partial
import logging

from discord import Colour, Embed, Interaction, TextChannel, User, app_commands
from discord.ext import commands
import human_readable
from cog.classes.scheduler_task import SchedulerTask

from cog.scheduler import SchedulerCog


def set_logger(logger: logging.Logger) -> None:
    logger.setLevel(logging.INFO)

    handler = logging.handlers.RotatingFileHandler(
        filename="reminder.log",
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


class ReminderCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        print("ReminderCog loaded")

    def _get_scheduler(self) -> SchedulerCog:
        scheduler = self.bot.get_cog("SchedulerCog")
        if scheduler is None:
            raise ValueError("SchedulerCog is not active or loaded.")
        return scheduler

    async def _reminder_callback(self, reminder: str, channel: TextChannel, user: User):
        await channel.send(f"Reminder: {reminder} <@{user}>")

    @app_commands.command(
        description="Create a reminder",
        name="remind",
    )
    async def remind(
        self,
        interaction: Interaction,
        reminder: str,
        days: int | None,
        hours: int | None,
        minutes: int | None,
        seconds: int | None,
    ):
        delta_expiry = timedelta(
            days=days or 0, hours=hours or 0, minutes=minutes or 0, seconds=seconds or 0
        )
        datetime_expiry = datetime.now() + delta_expiry

        try:
            scheduler = self._get_scheduler()
            await interaction.response.send_message(
                embed=Embed(
                    colour=Colour.random(),
                    title=f"Reminder for {interaction.user.display_name}",
                    description=reminder.capitalize(),
                    timestamp=datetime_expiry,
                ).add_field(
                    name="When:",
                    value=f"⠀⠀⤷ **{human_readable.precise_delta(delta_expiry)}**",
                )
            )
            # TODO: Save to database and register task
            scheduler.schedule_item(
                SchedulerTask(
                    expires_at=datetime_expiry,
                    task=partial(
                        self._reminder_callback,
                        reminder,
                        interaction.channel,
                        interaction.user,
                    ),
                )
            )
        except ValueError:
            await interaction.response.send_message(
                "Scheduler Cog has not been initialised, event scheduling is disabled."
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ReminderCog(bot))


async def teardown(bot: commands.Bot) -> None:
    await bot.remove_cog(ReminderCog(bot))
