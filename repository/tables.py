from datetime import datetime

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from repository.db_config import Base


class GuildModel(Base):
    __tablename__ = "guild"
    name: Mapped[str]
    id: Mapped[int] = mapped_column(primary_key=True)


class GameModel(Base):
    __tablename__ = "game"

    id: Mapped[int] = mapped_column(
        init=False, primary_key=True, autoincrement=True)
    name: Mapped[str]
    max_size: Mapped[int]
    guild_id: Mapped[int] = mapped_column(
        ForeignKey(
            "guild.id",
            ondelete='cascade'
        )
    )
    role: Mapped[int] = mapped_column(nullable=True, default=None)
    icon_url: Mapped[str] = mapped_column(nullable=True, default=None)


class MemberModel(Base):
    __tablename__ = "member"

    id: Mapped[int] = mapped_column(primary_key=True)
    join_datetime: Mapped[datetime] = mapped_column(default=datetime.now())

    def __repr__(self):
        return f"<member_id={self.id}\njoin_datetime={self.join_datetime})>"


class LobbyModel(Base):
    __tablename__ = "lobby"

    control_panel_message_id: Mapped[int]
    original_channel_id: Mapped[int]
    lobby_channel_id: Mapped[int]
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("member.id")
    )
    guild_id: Mapped[int] = mapped_column(
        ForeignKey("guild.id", ondelete="CASCADE"))
    game_id: Mapped[int] = mapped_column(
        ForeignKey(
            "game.id", ondelete="CASCADE"
        ),
        nullable=True
    )

    embed_message_id: Mapped[int] = mapped_column(nullable=True, default=None)
    queue_message_id: Mapped[int] = mapped_column(nullable=True, default=None)
    game_size: Mapped[int] = mapped_column(nullable=True, default=None)
    last_promotion_message_id: Mapped[int] = mapped_column(
        nullable=True,
        default=None
    )
    last_promotion_datetime: Mapped[datetime] = mapped_column(
        nullable=True,
        default=None
    )
    history_thread_id: Mapped[int] = mapped_column(nullable=True, default=None)
    description: Mapped[str] = mapped_column(
        default="No description provided."
    )
    id: Mapped[int] = mapped_column(
        init=False,
        primary_key=True,
        autoincrement=True
    )
    created_datetime: Mapped[datetime] = mapped_column(default=datetime.now())
    is_locked: Mapped[bool] = mapped_column(default=False)

    members: Mapped[list["MemberModel"]] = relationship(
        secondary="member_lobby",
        default_factory=list,
        lazy='joined',
        cascade="all, delete",
    )

    queue_members: Mapped[list["MemberModel"]] = relationship(
        secondary="queue_member_lobby",
        default_factory=list,
        lazy='joined',
        cascade="all, delete",
    )


class MemberLobbyModel(Base):
    __tablename__ = "member_lobby"

    lobby_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lobby.id",
            ondelete='cascade',
        ),
        primary_key=True,
    )

    member_id: Mapped[int] = mapped_column(
        ForeignKey(
            "member.id",
            ondelete='cascade'
        ),
        primary_key=True,
    )
    join_datetime: Mapped[datetime] = mapped_column(default=datetime.now())
    has_joined_vc: Mapped[bool] = mapped_column(Boolean, default=False)
    ready: Mapped[bool] = mapped_column(default=False)


class QueueMemberLobbyModel(Base):
    __tablename__ = "queue_member_lobby"
    lobby_id: Mapped[int] = mapped_column(
        ForeignKey(
            "lobby.id",
            ondelete='cascade'
        ),
        primary_key=True,
    )

    member_id: Mapped[int] = mapped_column(
        ForeignKey(
            "member.id",
            ondelete='cascade'
        ),
        primary_key=True,
    )
    join_datetime: Mapped[datetime] = mapped_column(default=datetime.now())
