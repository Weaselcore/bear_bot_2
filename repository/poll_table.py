import enum
from datetime import datetime
from turtle import color

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from repository.db_config import Base


class VoteType(enum.Enum):
    SINGLE_VOTE = 1
    MULTIPLE_VOTE = 2


class PollGuildModel(Base):
    __tablename__ = "poll_guild"
    name: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())
    conclusion_datetime: Mapped[datetime] = mapped_column(nullable=True, default=None)


class PollModel(Base):
    __tablename__ = "poll"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    question: Mapped[str] = mapped_column(nullable=False)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("poll_guild.id", ondelete="CASCADE")
    )
    vote_type: Mapped[VoteType] = mapped_column(nullable=False)
    colour: Mapped[str] = mapped_column(nullable=False)
    message_id: Mapped[int] = mapped_column(nullable=True, default=None)
    channel_id: Mapped[int] = mapped_column(nullable=True, default=None)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())
    is_active: Mapped[bool] = mapped_column(default=True)


class PollAnswerModel(Base):
    __tablename__ = "poll_answer"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    answer: Mapped[str] = mapped_column(nullable=False)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("poll.id", ondelete="CASCADE")
    )
    owner_id: Mapped[int] = mapped_column(nullable=False)
    url: Mapped[str] = mapped_column(nullable=True, default=None)
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class PollMemberAnswerModel(Base):
    __tablename__ = "poll_member_answer"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    poll_answer_id: Mapped[int] = mapped_column(
        ForeignKey("poll_answer.id", ondelete="CASCADE")
    )
    member_id: Mapped[int] = mapped_column(nullable=False)
    answer_datetime: Mapped[datetime] = mapped_column(default=func.now())