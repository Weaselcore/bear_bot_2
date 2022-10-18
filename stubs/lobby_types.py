from typing import Protocol

from discord import Member, User, Message, TextChannel
from datetime import datetime

from discord.ui import View


class Channel(Protocol):

    async def send(self, content: str | None = None, view: View | None = None) -> Message:
        ...


class LobbyState(Protocol):
    ...


class MemberState(Protocol):
    ...


class MemberModel(Protocol):
    member: Member
    join_datetime: datetime
    state: MemberState
    user: User


class LobbyEmbed(Protocol):

    def update(self) -> None:
        ...


class LobbyModel(Protocol):
    embed: LobbyEmbed
    members: list[MemberModel]
    status: LobbyState
    last_promotion_message: Message
    last_promotion_datetime: datetime
    owner: User
    lobby_channel: TextChannel
    description: str
    game_size: int
    created_datetime: datetime
    ...


class Client(Protocol):
    lobby: dict[int, LobbyModel] = {}
    ...

    def dispatch(self, event: str, lobby_id: int) -> None: ...


class UpdateEmbedType(Protocol):
    ...
