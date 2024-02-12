from datetime import datetime
from pydantic import BaseModel


class MemberModel(BaseModel):
    id: int
    join_date: datetime = datetime.utcnow()


class GuildModel(BaseModel):
    id: int
    name: str


class GameModel(BaseModel):
    id: int | None
    name: str
    max_size: int
    role: int
    guild_id: int
    icon_url: str | None


class MemberLobbyModel(BaseModel):
    lobby_id: int
    member_id: int
    has_joined_vc: bool
    join_datetime: datetime
    ready: bool


class QueueMemberLobbyModel(BaseModel):
    lobby_id: int
    member_id: int
    join_datetime: datetime


class LobbyModel(BaseModel):
    id: int
    description: str | None
    created_datetime: datetime
    embed_message_id: int
    game_id: int
    game_size: int
    guild_id: int
    history_thread_id: int
    is_locked: bool
    last_promotion_datetime: datetime
    last_promotion_message_id: int
    lobby_channel_id: int
    original_channel_id: int
    owner_id: int
    queue_message_id: int
    member_lobbies: list[MemberLobbyModel]
    queue_member_lobbies: list[QueueMemberLobbyModel]


class InsertLobbyModel(BaseModel):
    original_channel_id: int
    guild_id: int
    owner_id: int
    game_id: int
    game_size: int
    description: str | None


class InsertGameModel(BaseModel):
    name: str
    max_size: int
    role: int
    guild_id: int
    icon_url: str | None
