from datetime import datetime
import enum
from turtle import color
from repository.db_config import Base
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Enum
from sqlalchemy import ForeignKey, func


class PollType(enum.Enum):
    BINARY = 1
    MULTIPLE_CHOICE = 2


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
    poll_type: Mapped[PollType] = mapped_column(nullable=False)
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
    created_datetime: Mapped[datetime] = mapped_column(default=func.now())


class PollMemberAnswerModel(Base):
    __tablename__ = "poll_member_answer"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, init=False)
    poll_answer_id: Mapped[int] = mapped_column(
        ForeignKey("poll_answer.id", ondelete="CASCADE")
    )
    member_id: Mapped[int] = mapped_column(nullable=False)
    answer_datetime: Mapped[datetime] = mapped_column(default=func.now())