from dotenv import load_dotenv
import os
from sqlalchemy import BIGINT
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, MappedAsDataclass

load_dotenv()

DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ['PG_USER'],
    os.environ['PG_PASSWORD'],
    os.environ['PG_HOST'],
    os.environ['PG_PORT'],
    os.environ['PG_DATABASE']
)

engine = create_async_engine(
    DATABASE_URL,
    pool_size=3,
    future=True,
    echo=True,
)

async_session = sessionmaker(  # type: ignore
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)


class Base(MappedAsDataclass, DeclarativeBase, repr=True):  # type: ignore
    type_annotation_map = {
        int: BIGINT
    }
