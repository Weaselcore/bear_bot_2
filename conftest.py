import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from repository.db_config import Base
from repository.tables import GuildModel, LobbyModel, MemberModel

"""These fixtures are used to create a database for testing purposes. For now it tests
    the lobby cog feature. Change these to make the fixures more generalised for other 
    database tests.
"""

load_dotenv()

@pytest.fixture(scope="session", autouse=True)
def event_loop():
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def engine():
    async_engine = create_async_engine("postgresql+asyncpg://{}:{}@{}:{}/{}".format(
            os.environ["TEST_PG_USER"],
            os.environ["TEST_PG_PASSWORD"],
            os.environ["TEST_PG_HOST"],
            os.environ["TEST_PG_PORT"],
            os.environ["TEST_PG_DATABASE"],
        )
    )
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    yield async_engine
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async_engine.sync_engine.dispose()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_database(engine):

    async with engine.begin() as session:
        await session.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, expire_on_commit=True, class_=AsyncSession)

    async with async_session() as session:
        member = MemberModel(id=123)
        session.add(member)

        member2 = MemberModel(id=321)
        session.add(member2)

        await session.flush()

        lobby = LobbyModel(
            created_datetime=datetime.now(),
            original_channel_id=12,
            lobby_channel_id=34,
            control_panel_message_id=56,
            description="test",
            embed_message_id=78,
            queue_message_id=91,
            game_id="test",
            game_size=5,
            last_promotion_message_id=None,
            last_promotion_datetime=None,
            history_thread_id=12,
            is_locked=False,
            owner_id=member.id
        )
        
        lobby.members.append(member)
        lobby.queue_members.append(member2)

        guild = GuildModel(
            id=1,
            name="test",
        )

        lobby.guilds.append(guild)
        session.add(lobby)

        await session.commit()
    

@pytest_asyncio.fixture()
async def session(engine):
    async with engine.begin() as conn:
        async_session = sessionmaker(
            expire_on_commit=False,
            class_=AsyncSession,
            bind=conn
        )
        yield async_session
        await conn.rollback()