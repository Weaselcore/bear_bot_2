from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from time import gmtime, strftime
from typing import Optional, cast
from discord import Message, User, TextChannel, Embed, Thread, Member

from stubs.lobby_types import Client, LobbyEmbed


class MemberState(Enum):
    NOT_READY = 'Not Ready',
    READY = 'Ready',

    def __str__(self) -> str:
        return f'{ self.value[0].upper()}'


class LobbyState(Enum):
    LOCK = 'lock',
    UNLOCK = 'unlock',

    def __str__(self) -> str:
        return f'{ self.value[0].upper()}'


@dataclass
class MemberModel:
    member: User
    join_datetime = datetime.now()
    state = MemberState.NOT_READY

    def update(self) -> MemberState:
        if self.state == MemberState.READY:
            self.state = MemberState.NOT_READY
        else:
            self.state = MemberState.READY
        return self.state


@dataclass
class LobbyModel:
    # Use the message id as the lobby id
    control_panel: Message
    lobby_channel: TextChannel
    original_channel: TextChannel
    owner: User
    created_datetime = datetime.now()
    description: Optional[str] = None
    embed: Optional[Embed] = None
    embed_message: Optional[Message] = None
    game_code = 'gametype'
    game_size = 1
    last_promotion_message: Optional[Message] = None
    last_promotion_datetime: Optional[datetime] = None
    is_promoting = False
    members: list[MemberModel] = field(default_factory=list)
    thread: Optional[Thread] = None
    status = LobbyState.UNLOCK


class LobbyManager:

    @staticmethod
    def get_lobby(bot: Client, lobby_id: int) -> LobbyModel:
        lobby_dict: dict[int, LobbyModel] = bot.lobby
        lobby_model = lobby_dict[lobby_id]
        if lobby_model is None:
            raise ValueError('Lobby not found')
        return lobby_model

    @staticmethod
    def set_lobby(bot: Client, lobby_id: int, lobby: LobbyModel) -> None:
        lobby_dict: dict[int, LobbyModel] = bot.lobby
        lobby_dict[lobby_id] = lobby

    @staticmethod
    def get_thread(bot: Client, lobby_id: int) -> Optional[Thread]:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.thread

    @staticmethod
    def set_thread(bot: Client, lobby_id: int, thread: Thread) -> None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        lobby_model.thread = thread

    @staticmethod
    def get_gamecode(bot: Client, lobby_id: int) -> str:
        lobby_dict: dict[int, LobbyModel] = bot.lobby
        return lobby_dict[lobby_id].game_code

    @staticmethod
    def set_gamecode(bot: Client, lobby_id: int, game_code: str) -> LobbyModel:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        lobby_model.game_code = game_code
        return lobby_model

    @staticmethod
    def get_gamesize(bot: Client, lobby_id: int) -> int:
        lobby_dict: dict[int, LobbyModel] = bot.lobby
        return lobby_dict[lobby_id].game_size

    @staticmethod
    def set_gamesize(bot: Client, lobby_id: int, game_size: str) -> LobbyModel:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        lobby_model.game_size = int(game_size)
        return lobby_model

    @staticmethod
    def get_lobby_name(bot: Client) -> str:
        lobby_number = len(bot.lobby)
        return f'Lobby {lobby_number}'

    @staticmethod
    def get_lobby_id(bot: Client, lobby_id: int) -> TextChannel:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.lobby_channel

    @staticmethod
    def get_lobby_owner(bot: Client, lobby_id: int) -> User:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.owner

    @staticmethod
    def get_lobby_status(bot: Client, lobby_id: int) -> LobbyState:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.status

    @staticmethod
    def update_lobby_status(bot: Client, lobby_id: int) -> None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)

        if lobby_model.status == LobbyState.UNLOCK:
            lobby_model.status = LobbyState.LOCK
        else:
            lobby_model.status = LobbyState.UNLOCK

    @staticmethod
    def get_channel(bot: Client, lobby_id: int) -> TextChannel:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.lobby_channel

    @staticmethod
    def get_original_channel(bot: Client, lobby_id: int) -> TextChannel:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.original_channel

    @staticmethod
    def get_embed_message(bot: Client, lobby_id: int) -> Message | None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.embed_message

    @staticmethod
    def set_embed_message(bot: Client, lobby_id: int, embed_message: Message) -> None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        lobby_model.embed_message = embed_message

    @staticmethod
    def get_embed(bot: Client, lobby_id: int) -> LobbyEmbed | None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.embed

    @staticmethod
    def set_embed(bot: Client, lobby_id: int, embed: Embed) -> None:
        bot.lobby[lobby_id].embed = embed

    @staticmethod
    def get_members(bot: Client, lobby_id: int) -> list[MemberModel]:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.members

    @staticmethod
    def add_member(
        bot: Client,
        lobby_id: int,
        member: User
    ) -> bool:
        members = bot.lobby[lobby_id].members
        # Check if member is in the lobby
        for member_model in members:
            if member_model.user == member:
                return False
        # Add member to the lobby
        bot.lobby[lobby_id].members.append(MemberModel(member))
        return True

    @staticmethod
    def remove_member(
        bot: Client,
        lobby_id: int,
        member: User
    ) -> bool:
        members = bot.lobby[lobby_id].members
        # Check if member is in the lobby
        for member_model in members:
            if member_model.user.id == member.id:
                members.remove(member_model)
                return True
        return False

    @staticmethod
    def update_member_state(
        bot: Client,
        lobby_id: int,
        member: User
    ) -> MemberState | None:
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        for member_model in lobby_model.members:
            if member_model.member == member:
                member_state = member_model.update()
                return member_state
        return None

    @staticmethod
    def lock(bot: Client, lobby_id: int) -> LobbyState:
        new_status = None
        if bot.lobby[lobby_id].status == LobbyState.UNLOCK:
            new_status = LobbyState.LOCK
        elif bot.lobby[lobby_id].status == LobbyState.LOCK:
            new_status = LobbyState.UNLOCK
        if new_status is not None:
            bot.lobby[lobby_id].status = new_status
        else:
            raise ValueError("Invalid lobbystate found.")
        return new_status

    @staticmethod
    def has_joined(bot: Client, lobby_id: int, member: User) -> bool:
        for member_model in bot.lobby[lobby_id].members:
            if member_model.user.id == member.id:
                return True
        return False

    @staticmethod
    def switch_owner(
        bot: Client,
        lobby_id: int,
        member: Member
    ) -> None:
        """Swap a member with the owner of the lobby"""
        # Check if the member is in the lobby
        has_joined = LobbyManager.has_joined(bot, lobby_id, cast(User, member))

        if has_joined and member != LobbyManager.get_lobby_owner(bot, lobby_id):
            bot.lobby[lobby_id].owner = member
            member_list = bot.lobby[lobby_id].members
            for index, member_model in enumerate(member_list):
                if member_model.user == member:
                    new_owner = bot.lobby[lobby_id].members.pop(index)
                    old_owner = bot.lobby[lobby_id].members.pop(0)
                    bot.lobby[lobby_id].members.insert(0, new_owner)
                    bot.lobby[lobby_id].members.append(old_owner)
                    break

    @staticmethod
    def search_new_owner(bot: Client, lobby_id: int) -> bool:
        """Choose the next owner in lobby and move next owner up to first slot"""

        # Check if there is no other member in the lobby
        if len(bot.lobby[lobby_id].members) == 1:
            return False

        # Get the next owner
        new_owner = bot.lobby[lobby_id].members[1].user
        bot.lobby[lobby_id].owner = new_owner
        bot.lobby[lobby_id].members[0], bot.lobby[lobby_id].members[1] = \
            bot.lobby[lobby_id].members[1], bot.lobby[lobby_id].members[0]
        return True

    @staticmethod
    def remove_owner(bot: Client, lobby_id: int) -> bool:
        # Check if there is no other member in the lobby
        if len(bot.lobby[lobby_id].members) == 1:
            return False

        # Get the next owner
        new_owner = bot.lobby[lobby_id].members[1].user
        bot.lobby[lobby_id].owner = new_owner
        bot.lobby[lobby_id].members.pop(0)
        return True

    @staticmethod
    def get_member_length(bot: Client, lobby_id: int) -> int:
        """Get the number of members in the lobby"""
        return len(bot.lobby[lobby_id].members)

    @staticmethod
    def get_members_ready(bot: Client, lobby_id: int) -> list[User]:
        """Get the number of members that are ready"""
        members = [member_model.user for member_model in bot.lobby[lobby_id]
                   .members if member_model.state == MemberState.READY]
        return members

    @staticmethod
    def get_members_not_ready(bot: Client, lobby_id: int) -> list[User]:
        """Get the number of members that are not ready"""
        members = [member_model.user for member_model in bot.lobby[lobby_id].members
                   if member_model.state == MemberState.NOT_READY]
        return members

    @staticmethod
    def get_lobby_lock(bot: Client, lobby_id: int) -> LobbyState:
        """Get the lock state of the lobby"""
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.status

    @staticmethod
    async def delete_lobby(bot: Client, lobby_id: int) -> None:
        lobby_data = bot.lobby[lobby_id]
        # Delete channel
        channel = lobby_data.lobby_channel
        await channel.delete()
        # Delete lobby data
        bot.lobby.pop(lobby_id)

    @staticmethod
    def set_descriptor(bot: Client, lobby_id: int, description: str) -> None:
        """Set the description of the lobby"""
        bot.lobby[lobby_id].description = description

    @staticmethod
    def get_descriptor(bot: Client, lobby_id: int) -> str | None:
        """Get the description of the lobby"""
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.description

    @staticmethod
    def is_full(bot: Client, lobby_id: int) -> bool:
        """Check if the lobby is full"""
        if int(bot.lobby[lobby_id].game_size) == len(bot.lobby[lobby_id].members):
            return True
        else:
            return False

    @staticmethod
    def get_session_time(bot: Client, lobby_id: int) -> str:
        """Get the session time of the lobby"""
        creation: datetime = bot.lobby[lobby_id].created_datetime
        deletion = datetime.now()
        duration = deletion - creation
        return "Session Duration: " + strftime("%H:%M:%S", gmtime(duration.total_seconds()))

    @staticmethod
    def get_last_promotion_message(bot: Client, lobby_id: int) -> Message | None:
        """Get the last promotion message"""
        lobby_model = LobbyManager.get_lobby(bot, lobby_id)
        return lobby_model.last_promotion_message

    @staticmethod
    def can_promote(bot: Client, lobby_id: int) -> bool:
        """Check if last promotion message is older than 10 minutes"""
        if bot.lobby[lobby_id].last_promotion_message is None:
            return True
        else:
            last_promotion_datetime = bot.lobby[lobby_id].last_promotion_datetime
            if datetime.now() - last_promotion_datetime > timedelta(minutes=10):
                return True
            else:
                return False

    @staticmethod
    def set_last_promotion_message(
        bot: Client,
        lobby_id: int,
        message: Message
    ) -> None:
        """Set the last promotion message"""
        bot.lobby[lobby_id].last_promotion_message = message
        bot.lobby[lobby_id].last_promotion_datetime = datetime.now()

    @staticmethod
    def get_unready_mentions(bot: Client, lobby_id: int) -> str | None:
        members_to_ping = LobbyManager.get_members_not_ready(bot, lobby_id)
        if len(members_to_ping) == 0:
            return None
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @staticmethod
    def get_ready_mentions(bot: Client, lobby_id: int) -> str | None:
        members_to_ping = LobbyManager.get_members_ready(bot, lobby_id)
        if len(members_to_ping) == 0:
            return None
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @staticmethod
    def get_new_owner_mention(bot: Client, lobby_id: int) -> str:
        return f'<@{LobbyManager.get_lobby_owner(bot, lobby_id).id}>'
