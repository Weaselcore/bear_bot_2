from sqlalchemy import BIGINT
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Base(MappedAsDataclass, DeclarativeBase, repr=True):
    type_annotation_map = {int: BIGINT}


class DatabaseManager:

    @staticmethod
    async def create_tables(tables: list[Base], engine: AsyncEngine) -> None:
        # Create all tables if they don't exist
        async with engine.begin() as conn:
            await conn.run_sync(
                Base.metadata.create_all,
                tables=[table.__table__ for table in tables],
            )

    @staticmethod
    def create_engine(
        username: str,
        password: str,
        host: str,
        port: str,
        database_name: str,
    ) -> AsyncEngine:
        database_url = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
            username,
            password,
            host,
            port,
            database_name,
        )

        # Create database engine
        return create_async_engine(
            database_url,
            pool_size=3,
            future=True,
            echo=False,
        )

    @staticmethod
    def create_async_session_maker(
        engine: AsyncEngine
    ) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            engine,
            expire_on_commit=False,
        )
