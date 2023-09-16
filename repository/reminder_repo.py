from datetime import datetime
from discord import Guild
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repository.table.reminder_table import ReminderGuildModel, ReminderModel


class ReminderRepository:
    def __init__(self, database: async_sessionmaker[AsyncSession]):
        self.database = database

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
        guild: Guild,
        mention_ids: list[int] | None,
        expire_at: datetime,
    ) -> int:
        guild_model = await self.get_guild(guild.id)
        if guild_model is None:
            guild_id = await self.add_guild(guild_id=guild.id, guild_name=guild.name)

        async with self.database() as session:
            async with session.begin():
                reminder = ReminderModel(
                    owner_id=owner_id,
                    expire_at=expire_at,
                    guild_id=guild_model.id or guild_id
                )
                session.add(reminder)
                await session.commit()
                return reminder.id

    async def get_reminder(
        self,
        id: int,
    ) -> ReminderModel:
        async with self.database() as session:
            async with session.begin():
                reminder = await session.get(ReminderModel, id)
                if reminder is None:
                    raise ValueError(
                        f"Reminder could not be found with id: {id}")
                return reminder

    async def remove_reminder(
        self,
        id: int,
    ):
        async with self.database() as session:
            async with session.begin():
                try:
                    reminder = self.get_reminder(id)
                    await session.delete(reminder)
                    await session.commit()
                except ValueError:
                    raise
