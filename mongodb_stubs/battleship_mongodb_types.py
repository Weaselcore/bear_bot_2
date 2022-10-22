from datetime import datetime

from bson import ObjectId
from pydantic import BaseModel, Field

from mongodb_stubs.mongo_util import PyObjectId


class MongoMemberModel(BaseModel):
    member_id: int
    join_datetime: datetime = datetime.now()
    is_ready: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True


class MongoLobbyModel(BaseModel):
    id: PyObjectId | None = Field(default_factory=PyObjectId, alias="_id")
    guild_id: int
    control_message_id: int
    lobby_channel_id: int
    original_channel_id: int
    owner_id: int
    created_datetime = datetime.now()
    description: str | None
    embed_message_id: int | None
    game_code: str = 'gametype'
    game_size: int = 5
    last_promotion_message_id: int | None
    last_promotion_datetime: datetime | None
    is_promoting: bool = False
    members: list[MongoMemberModel] = []
    thread_id: int
    is_locked: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UpdateLobbyModel(BaseModel):
    guild_id: int
    control_message: int
    lobby_channel: int
    original_channel: int
    owner: int
    created_datetime = datetime.now()
    description: str | None
    embed_message: int | None
    game_code = str
    game_size = int
    last_promotion_message: int | None
    last_promotion_datetime: datetime | None
    is_promoting = bool
    members: list[MongoMemberModel]
    thread: int | None
    is_locked: bool = False

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
