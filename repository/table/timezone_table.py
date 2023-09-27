from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from repository.db_config import Base


class TimezoneGuildModel(Base):
    __tablename__ = "timezone_guild"
    name: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class TimezoneUserModel(Base):
    __tablename__ = "timezone_user"
    # User_id should be the primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    timezone: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("timezone_guild.id", ondelete="CASCADE")
    )
