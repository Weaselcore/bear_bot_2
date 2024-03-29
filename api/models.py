from datetime import datetime
from enum import IntEnum
from pydantic import BaseModel


class MemberModel(BaseModel):
    id: int
    join_datetime: datetime = datetime.now()


class GuildModel(BaseModel):
    id: int
    name: str


class GameModel(BaseModel):
    id: int | None
    name: str
    max_size: int
    role: int | None
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


class LobbyStates(IntEnum):
    ACTIVE = 1
    LOCKED = 2
    PENDING_DELETION = 3


class LobbyModel(BaseModel):
    id: int
    description: str | None = None
    created_datetime: datetime
    embed_message_id: int | None = None
    game_id: int
    game_size: int
    guild_id: int
    history_thread_id: int | None = None
    state: LobbyStates = LobbyStates.ACTIVE
    last_promotion_message_id: int | None = None
    last_promotion_datetime: datetime | None = None
    last_deletion_message_id: int | None = None
    last_deletion_datetime: datetime | None = None
    lobby_channel_id: int | None = None
    original_channel_id: int
    owner_id: int
    queue_message_id: int | None = None
    member_lobbies: list[MemberLobbyModel] = []
    queue_member_lobbies: list[QueueMemberLobbyModel] = []


class InsertLobbyModel(BaseModel):
    original_channel_id: int
    guild_id: int
    guild_name: str
    owner_id: int
    game_id: int
    game_size: int
    description: str | None = None
    state: LobbyStates = LobbyStates.ACTIVE


class InsertGameModel(BaseModel):
    name: str
    max_size: int
    guild_id: int
    role: int | None = None
    icon_url: str | None = None


class MessageResponseModel(BaseModel):
    title: str
    description: str
    # Pydantic requires this field to have a default of None or it errors.
    additional_field: str | None = None


class LobbyResponseModel(BaseModel):
    data: LobbyModel
    message: MessageResponseModel

    def unwrap(self) -> tuple[LobbyModel, MessageResponseModel]:
        return self.data, self.message,

class MultipleLobbyResponseModel(BaseModel):
    data: list[LobbyModel] = []
    message: MessageResponseModel

    def unwrap(self) -> tuple[list[LobbyModel], MessageResponseModel]:
        return self.data, self.message,

class GameResponseModel(BaseModel):
    data: GameModel
    message: MessageResponseModel

    def unwrap(self) -> tuple[GameModel, MessageResponseModel]:
        return self.data, self.message,


class MultipleGameResponseModel(BaseModel):
    data: list[GameModel] = []
    message: MessageResponseModel

    def unwrap(self) -> tuple[list[GameModel], MessageResponseModel]:
        return self.data, self.message,
