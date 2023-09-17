from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

from repository.db_config import Base
from repository.reminder_repo import ReminderRepository
from repository.table.reminder_table import ReminderGuildModel, ReminderModel


@dataclass
class Guild:
    """Custom guild object, repository uses a protocol instead of discord.py Guild object"""

    id: int
    name: str


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_database(engine):
    """Test specific: Seed database with example entries"""
    async with engine.begin() as session:
        await session.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=True, class_=AsyncSession)

    async with async_session() as session:
        guild = ReminderGuildModel(id=1, name="test_guild")
        session.add(guild)
        await session.flush()
        reminder = ReminderModel(
            reminder="test_reminder",
            owner_id=1,
            channel_id=1,
            expire_at=datetime.now() + timedelta(weeks=10),
            guild_id=guild.id,
        )
        session.add(reminder)
        await session.commit()


class TestReminderRepository:
    @pytest.mark.asyncio
    async def test_get_reminder(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        reminder = await reminder_repository.get_reminder(id=1)
        assert reminder.id == 1

    @pytest.mark.asyncio
    async def test_all_active_reminders(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        assert len(await reminder_repository.get_all_active_reminders()) == 1

    @pytest.mark.asyncio
    async def test_get_all_reminders_by_guild_id(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        assert (
            len(await reminder_repository.get_all_reminders_by_guild_id(guild_id=1))
            == 1
        )

    @pytest.mark.asyncio
    async def test_get_all_active_reminders_by_user_id(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        assert (
            len(
                await reminder_repository.get_all_active_reminders_by_user_id(user_id=1)
            )
            == 1
        )

    @pytest.mark.asyncio
    async def test_get_guild(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        guild = await reminder_repository.get_guild(guild_id=1)
        assert guild.name == "test_guild"

    @pytest.mark.asyncio
    async def test_add_guild(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        guild_id = await reminder_repository.add_guild(
            guild_id=2, guild_name="test_guild_2"
        )
        guild = await reminder_repository.get_guild(guild_id=2)
        assert guild.id == guild_id

    @pytest.mark.asyncio
    async def test_create_reminders(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        id = await reminder_repository.add_reminder(
            owner_id=1,
            channel_id=1,
            reminder="test reminder",
            guild=Guild(id=1, name="test_guild"),
            expire_at=datetime.now() + timedelta(seconds=5),
        )
        reminder = await reminder_repository.get_reminder(id=id)
        assert reminder.id == id

    @pytest.mark.asyncio
    async def test_remove_reminders(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        id = await reminder_repository.remove_reminder(1)
        with pytest.raises(Exception) as exc_info:
            await reminder_repository.get_reminder(1)
        assert str(exc_info.value) == f"Reminder could not be found with id: {id}"

    @pytest.mark.asyncio
    async def test_update_reminder_has_triggered(self, session: AsyncSession):
        reminder_repository = ReminderRepository(session)
        before_update = await reminder_repository.get_reminder(1)
        await reminder_repository.update_reminder_has_triggered(1)
        after_update = await reminder_repository.get_reminder(1)
        assert (
            before_update.has_triggered == False and after_update.has_triggered == True
        )
