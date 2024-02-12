from datetime import datetime
from pydantic import BaseModel


class Member(BaseModel):
    id: int
    join_date: datetime


class Guild(BaseModel):
    id: int
    name: str


class Game(BaseModel):
    id: int
    icon_url: str
    max_size: int
    role: int
    guild_id: int


class Lobby(BaseModel):
    id: int
    description: str
    control_panel_message_id: int
    created_timezone: datetime
    embed_message_id: int
    game_id: int
    game_size: int
    history_thread_id: int
    is_locked: bool
    last_promotion_datetime: datetime
    last_promotion_message_id: int
    lobby_channel_id: int
    original_channel_id: int
    owner_id: int
    queue_message_id: int
    member: list[Member]


class MemberLobby:
    lobby_id: int
    member_id: int
    has_joined_vc: bool
    join_datetime: datetime
    ready: bool


class QueueMemberLobby:
    lobby_id: int
    member_id: int
    join_datetime: datetime
