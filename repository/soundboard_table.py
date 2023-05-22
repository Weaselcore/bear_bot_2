from datetime import datetime
from enum import Enum, auto
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.properties import ForeignKey
from sqlalchemy.sql import func

from repository.db_config import Base


class SoundBiteGuild(Base):
    __tablename__ = "sb_guild"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    control_panel_message_id: Mapped[int | None] = mapped_column(nullable=False)
    channel_id: Mapped[int | None] = mapped_column(nullable=False)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class Soundbite(Base):
    __tablename__ = "soundbite"
    id: Mapped[str] = mapped_column(primary_key=True)
    soundbite_name: Mapped[str] = mapped_column(nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    file_size: Mapped[float] = mapped_column(nullable=False)
    file_path: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sb_guild.id",
            ondelete='cascade'
        )
    )
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class SoundbiteGuildAssociation(Base):
    __tablename__ = "soundbite_sb_guild"
    id: Mapped[int] = mapped_column(primary_key=True, init=False)
    soundbite_id: Mapped[int] = mapped_column(
        ForeignKey("soundbite.id",ondelete='cascade'),
        primary_key=True,
    )
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("sb_guild.id", ondelete='cascade'),
        primary_key=True,
    )
    play_count: Mapped[int] = mapped_column(default=0)


class SoundBiteCategory(Base):
    __tablename__ = "sb_category"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    message_id: Mapped[int | None]
    guild_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sb_guild.id",
            ondelete='cascade'
        )
    )
    soundbite_view_messages: Mapped[list["SoundbiteViewMessage"]] = relationship(init=False)
    priority: Mapped[int] = mapped_column(default=0)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class SoundbiteViewMessage(Base):
    __tablename__ = "sb_view_message"
    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "sb_category.id",
            ondelete='cascade'
        )
    )
