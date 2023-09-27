from typing import Protocol
from sqlalchemy import Result, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from repository.table.timezone_table import TimezoneGuildModel, TimezoneUserModel


class Guild(Protocol):
    id: int
    name: str


class TimezoneRepository:
    def __init__(self, database: async_sessionmaker[AsyncSession]):
        self.database = database

    async def get_guild(self, guild_id: int) -> TimezoneGuildModel | None:
        async with self.database() as session:
            async with session.begin():
                guild = await session.get(TimezoneGuildModel, guild_id)
                return guild

    async def add_guild(self, guild_id: int, guild_name: str) -> int:
        async with self.database() as session:
            async with session.begin():
                session.add(
                    TimezoneGuildModel(
                        id=guild_id,
                        name=guild_name,
                    )
                )
                await session.commit()
                return guild_id

    async def register_timezone(
        self,
        user_id: int,
        timezone: str,
        guild: Guild
    ) -> int:
        guild_id = None
        guild_model = await self.get_guild(guild.id)
        if guild_model is None:
            guild_id = await self.add_guild(guild_id=guild.id, guild_name=guild.name)

        async with self.database() as session:
            async with session.begin():
                timezone_user_model = TimezoneUserModel(
                    id=user_id,
                    timezone=timezone,
                    guild_id=guild_id or guild_model.id
                )
                session.add(timezone_user_model)
                await session.commit()
                return timezone_user_model.id

    async def update_timezone(
        self,
        user_id: int,
        timezone: str
    ) -> tuple[str, str]:
        async with self.database() as session:
            async with session.begin():
                user = await session.get(TimezoneUserModel, user_id)
                if user is None:
                    raise ValueError(
                        f"User with id: {user_id} does not have a timezone registered.")
                old_timezone = user.timezone
                user.timezone = timezone
                await session.commit()
                return old_timezone, user.timezone,

    async def get_all_registered_timezones(
        self,
        guild_id: int
    ) -> list[str]:
        async with self.database() as session:
            async with session.begin():
                result: Result = await session.execute(
                    select(TimezoneUserModel.timezone).where(
                        TimezoneUserModel.guild_id == guild_id
                    )
                )
                return list(result.scalars().unique().all())

    async def get_timezone_of_user(
        self,
        user_id: int
    ) -> str:
        async with self.database() as session:
            async with session.begin():
                user = await session.get(TimezoneUserModel, user_id)
                if user is None:
                    raise ValueError(
                        f"User with id: {user_id} does not have a timezone registered.")
                return user.timezone
