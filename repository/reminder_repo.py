from datetime import datetime

from discord import Guild
from sqlalchemy import Result, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repository.table.reminder_table import ReminderGuildModel, ReminderModel


class ReminderRepository:
    def __init__(self, database: async_sessionmaker[AsyncSession]):
        self.database = database

    async def get_all_active_reminders(self) -> list[ReminderModel]:
        async with self.database() as session:
            async with session.begin():
                result: Result = await session.execute(
                    select(ReminderModel).where(ReminderModel.has_triggered == False)
                )
                return list(result.scalars().unique().all())

    async def get_all_reminders_by_guild_id(self, guild_id: int) -> list[ReminderModel]:
        async with self.database() as session:
            async with session.begin():
                result: Result = await session.execute(
                    select(ReminderModel).where(ReminderModel.guild_id == guild_id)
                )
                return list(result.scalars().unique().all())

    async def get_all_active_reminders_by_user_id(
        self, user_id: int
    ) -> list[ReminderModel]:
        async with self.database() as session:
            async with session.begin():
                result: Result = await session.execute(
                    select(ReminderModel).where(
                        ReminderModel.owner_id == user_id,
                        ReminderModel.has_triggered == False,
                    )
                )
                return list(result.scalars().unique().all())

    async def get_guild(self, guild_id: int) -> ReminderGuildModel | None:
        async with self.database() as session:
            async with session.begin():
                guild = await session.get(ReminderGuildModel, guild_id)
                return guild

    async def add_guild(self, guild_id: int, guild_name: str) -> int:
        async with self.database() as session:
            async with session.begin():
                session.add(
                    ReminderGuildModel(
                        id=guild_id,
                        name=guild_name,
                    )
                )
                await session.commit()
                return guild_id

    async def add_reminder(
        self,
        owner_id: int,
        channel_id: int,
        reminder: str,
        guild: Guild,
        expire_at: datetime,
    ) -> int:
        guild_id = None
        guild_model = await self.get_guild(guild.id)
        if guild_model is None:
            guild_id = await self.add_guild(guild_id=guild.id, guild_name=guild.name)

        async with self.database() as session:
            async with session.begin():
                reminder_model = ReminderModel(
                    owner_id=owner_id,
                    channel_id=channel_id,
                    reminder=reminder,
                    expire_at=expire_at,
                    guild_id=guild_id or guild_model.id,
                )
                session.add(reminder_model)
                await session.commit()
                return reminder_model.id

    async def get_reminder(
        self,
        id: int,
    ) -> ReminderModel:
        async with self.database() as session:
            async with session.begin():
                reminder = await session.get(ReminderModel, id)
                if reminder is None:
                    raise ValueError(f"Reminder could not be found with id: {id}")
                return reminder

    async def remove_reminder(
        self,
        id: int,
    ) -> int:
        async with self.database() as session:
            async with session.begin():
                try:
                    reminder = await self.get_reminder(id)
                    await session.delete(reminder)
                    await session.commit()
                    return id
                except ValueError:
                    raise

    async def update_reminder_has_triggered(self, id: int):
        async with self.database() as session:
            async with session.begin():
                try:
                    reminder = await session.get(ReminderModel, id)
                    reminder.has_triggered = True
                    await session.commit()
                except ValueError:
                    raise
