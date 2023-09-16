from datetime import datetime
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from repository.db_config import Base


class ReminderGuildModel(Base):
    __tablename__ = "reminder_guild"
    name: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class ReminderModel(Base):
    __tablename__ = "reminder"
    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, init=False)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    mention_ids: Mapped[list[int]] = mapped_column(nullable=True)
    expire_at: Mapped[datetime] = mapped_column(nullable=False)
    has_triggered: Mapped[bool] = mapped_column(default=False)
    guild_id: Mapped[int] = mapped_column(ForeignKey(
        "reminder_guild.id", ondelete="CASCADE"
    ))
