import logging
from datetime import datetime
import os
from pathlib import Path
from dateutil.relativedelta import relativedelta

from discord import Interaction, app_commands
from discord.ext import commands
from dotenv import load_dotenv
import human_readable
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from manager.reminder_service import ReminderManager
from repository.db_config import Base
from repository.reminder_repo import ReminderRepository
from repository.table.reminder_table import ReminderGuildModel, ReminderModel

load_dotenv()

# Construct database url from environment variables
DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ["R_PG_USER"],
    os.environ["R_PG_PASSWORD"],
    os.environ["R_PG_HOST"],
    os.environ["R_PG_PORT"],
    os.environ["R_PG_DATABASE"],
)

# Create database engine
engine = create_async_engine(
    DATABASE_URL,
    pool_size=3,
    future=True,
    echo=False,
)


# This is the database session factory, invoking this variable creates a new session
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

def set_logger(logger: logging.Logger) -> None:
    logger.setLevel(logging.INFO)

    log_dir = Path("logs")

    handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "reminder.log",
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


class ReminderCog(commands.GroupCog, group_name="reminder"):
    def __init__(self, bot: commands.Bot, reminder_manager: ReminderManager) -> None:
        self.bot = bot
        self.reminder_manager = reminder_manager
        print("ReminderCog loaded")

        bot.loop.create_task(reminder_manager.populate_scheduler())

    @app_commands.command(
        description="Create a reminder",
        name="create",
    )
    async def create_reminders(
        self,
        interaction: Interaction,
        reminder: str,
        years: int | None,
        months: int | None,
        weeks: int | None,
        days: int | None,
        hours: int | None,
        minutes: int | None,
        seconds: int | None,
    ):

        delta_expiry = relativedelta(
            years=years or 0,
            months=months or 0,
            weeks=weeks or 0,
            days=days or 0,
            hours=hours or 0,
            minutes=minutes or 0,
            seconds=seconds or 0
        )

        current_date = datetime.now()
        datetime_expiry = current_date + delta_expiry
        end_date = current_date + delta_expiry
        # Convert the relativedelta to a timedelta for the human_readable library.
        delta = end_date - current_date

        await self.reminder_manager.create_reminder(
            interaction=interaction,
            reminder=reminder,
            owner_id=interaction.user.id,
            guild=interaction.guild,
            expire_at=datetime_expiry,
            delta=delta
        )

    @app_commands.command(
        description="List all your reminders",
        name="list",
    )
    async def list_reminders(self, interaction: Interaction):
        message = "*You have no active reminders.*"
        reminders = await self.reminder_manager.get_all_active_reminders_by_user_id(interaction.user.id)
        if len(reminders) != 0:
            message = '\n'.join([f"[ ID:{reminder.id} ] **{reminder.reminder}**: {human_readable.precise_delta(reminder.expire_at - datetime.now())}" for reminder in reminders])

        await interaction.response.send_message(message)

    @app_commands.command(
        description="Delete a reminder",
        name="delete",
    )
    async def delete_reminder(self, interaction: Interaction, id: int):
        await self.reminder_manager.delete_reminder(
            interaction=interaction,
            reminder_id=id
        )

async def setup(bot: commands.Bot) -> None:
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                ReminderModel.__table__,
                ReminderGuildModel.__table__,

            ],
        )
    # Create dependencies
    reminder_repository = ReminderRepository(async_session)
    reminder_manager = ReminderManager(bot=bot, repository=reminder_repository)

    await bot.add_cog(ReminderCog(bot, reminder_manager))


async def teardown(bot: commands.Bot) -> None:
    await bot.remove_cog(ReminderCog(bot))
