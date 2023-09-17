import asyncio
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from repository.db_config import Base

"""These fixtures are used to create a database for testing purposes. For now it tests
    the lobby cog feature. Change these to make the fixures more generalised for other 
    database tests.
"""

@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """Fixture to set the event loop policy"""
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def engine():
    """Automatic creation and deletion logic for test database."""
    async_engine = create_async_engine(
        "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
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

@pytest_asyncio.fixture()
async def session(engine):
    # Setup the engine and automatic rollback
    async with engine.begin() as conn:
        async_session = sessionmaker(
            expire_on_commit=False, class_=AsyncSession, bind=conn
        )
        yield async_session
        await conn.rollback()