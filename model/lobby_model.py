from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from time import gmtime, strftime
from typing import Protocol
import discord

from view.lobby.embeds import LobbyEmbed


class MemberState(Enum):
    NOT_READY = 'Not Ready',
    READY = 'Ready',

    def __str__(self):
        return f'{ self.value[0].upper()}'


class LobbyState(Enum):
    LOCK = 'lock',
    UNLOCK = 'unlock',

    def __str__(self):
        return f'{ self.value[0].upper()}'


@dataclass
class MemberModel:
    member: discord.Member
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
    control_panel: discord.Message
    lobby_channel: discord.TextChannel
    original_channel: discord.TextChannel
    owner: discord.Member
    created_datetime = datetime.now()
    description: str | None = None
    embed: LobbyEmbed| None = None
    embed_message: discord.Message | None = None
    queue_message: discord.Message | None = None
    game_code = 'gametype'
    game_size = 1
    last_promotion_message: discord.Message | None = None
    last_promotion_datetime: datetime | None = None
    is_promoting = False
    members: list[MemberModel] = field(default_factory=list)
    members_queue: list[MemberModel] = field(default_factory=list)
    thread: discord.Thread | None = None
    status = LobbyState.UNLOCK


class LobbyBot(Protocol):
    lobby: dict[int, LobbyModel]


class LobbyManager:

    @classmethod
    def get_lobby(cls, bot: LobbyBot, lobby_id: int) -> LobbyModel:
        try:
            return bot.lobby[lobby_id]
        except KeyError:
            raise KeyError(f'Lobby {lobby_id} does not exist.')

    @classmethod
    def set_lobby(cls, bot: LobbyBot, lobby_id: int, lobby: LobbyModel) -> None:
        bot.lobby[lobby_id] = lobby

    @classmethod
    def get_thread(cls, bot: LobbyBot, lobby_id: int) -> discord.Thread | None:
        return cls.get_lobby(bot, lobby_id).thread

    @classmethod
    def set_thread(cls, bot: LobbyBot, lobby_id: int, thread: discord.Thread) -> None:
        cls.get_lobby(bot, lobby_id).thread = thread

    @classmethod
    def get_gamecode(cls, bot: LobbyBot, lobby_id: int) -> str:
        return cls.get_lobby(bot, lobby_id).game_code

    @classmethod
    def set_gamecode(cls, bot: LobbyBot, lobby_id: int, game_code: str) -> None:
        cls.get_lobby(bot, lobby_id).game_code = game_code

    @classmethod
    def get_gamesize(cls, bot: LobbyBot, lobby_id: int) -> int:
        return cls.get_lobby(bot, lobby_id).game_size

    @classmethod
    def set_gamesize(cls, bot: LobbyBot, lobby_id: int, game_size: int) -> None:
        cls.get_lobby(bot, lobby_id).game_size = game_size

    @classmethod
    def get_lobby_name(cls, bot: LobbyBot) -> str:
        lobby_number = len(bot.lobby)
        return f'Lobby {lobby_number}'

    @classmethod
    def get_lobby_id(cls, bot: LobbyBot, lobby_id: int) -> discord.TextChannel:
        return cls.get_lobby(bot, lobby_id).lobby_channel

    @classmethod
    def get_lobby_owner(cls, bot: LobbyBot, lobby_id: int) -> discord.Member:
        return cls.get_lobby(bot, lobby_id).owner

    @classmethod
    def print_lobby(cls, bot: LobbyBot, lobby_id: int) -> None:
        print(cls.get_lobby(bot, lobby_id))

    @classmethod
    def get_lobby_status(cls, bot: LobbyBot, lobby_id: int) -> LobbyState:
        return cls.get_lobby(bot, lobby_id).status

    @classmethod
    def update_lobby_status(cls, bot: LobbyBot, lobby_id: int) -> None:
        lobby_model = cls.get_lobby(bot, lobby_id)

        if lobby_model.status == LobbyState.UNLOCK:
            lobby_model.status = LobbyState.LOCK
        else:
            lobby_model.status = LobbyState.UNLOCK

    @classmethod
    def get_channel(cls, bot: LobbyBot, lobby_id: int) -> discord.TextChannel:
        return cls.get_lobby(bot, lobby_id).lobby_channel

    @classmethod
    def get_original_channel(cls, bot: LobbyBot, lobby_id: int) -> discord.TextChannel:
        return cls.get_lobby(bot, lobby_id).original_channel

    @classmethod
    def get_control_panel(cls, bot: LobbyBot, lobby_id: int) -> discord.Message:
        return cls.get_lobby(bot, lobby_id).control_panel

    @classmethod
    def get_embed_message(cls, bot: LobbyBot, lobby_id: int) -> discord.Message | None:
        return cls.get_lobby(bot, lobby_id).embed_message

    @classmethod
    def set_embed_message(cls, bot: LobbyBot, lobby_id: int, embed_message: discord.Message) -> None:
        cls.get_lobby(bot, lobby_id).embed_message = embed_message

    @classmethod
    def get_queue_embed_message(cls, bot: LobbyBot, lobby_id: int) -> None | discord.Message:
        return cls.get_lobby(bot, lobby_id).queue_message

    @classmethod
    def set_queue_embed_message(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        queue_message: discord.Message
    ) -> None:
        cls.get_lobby(bot, lobby_id).queue_message = queue_message

    @classmethod
    def get_embed(cls, bot: LobbyBot, lobby_id: int) -> discord.Embed | None:
        return cls.get_lobby(bot, lobby_id).embed

    @classmethod
    def set_embed(cls, bot: LobbyBot, lobby_id: int, embed: discord.Embed) -> None:
        cls.get_lobby(bot, lobby_id).embed = embed

    @classmethod
    def get_queue_embed(cls, bot: LobbyBot, lobby_id: int) -> discord.Embed | None:
        return cls.get_lobby(bot, lobby_id).queue_embed

    @classmethod
    def set_queue_embed(cls, bot: LobbyBot, lobby_id: int, queue_embed: discord.Embed) -> None:
        cls.get_lobby(bot, lobby_id).queue_embed = queue_embed

    @classmethod
    def get_members(cls, bot: LobbyBot, lobby_id: int) -> list[MemberModel]:
        return cls.get_lobby(bot, lobby_id).members

    @classmethod
    def get_queue_members(cls, bot: LobbyBot, lobby_id: int) -> list[MemberModel]:
        return cls.get_lobby(bot, lobby_id).members_queue

    @classmethod
    def add_member(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        member: discord.Member
    ) -> bool:
        lobby = cls.get_lobby(bot, lobby_id)
        members = lobby.members
        # Check if member is in the lobby
        for member_model in members:
            if member_model.member == member:
                return False
        # Add member to the lobby
        lobby.members.append(MemberModel(member))
        return True

    @classmethod
    def add_member_queue(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        member: discord.Member
    ) -> bool:
        lobby = cls.get_lobby(bot, lobby_id)
        members = lobby.members
        members_queue = lobby.members_queue
        # Check if member is in the lobby
        for member_model in members:
            if member_model.member == member:
                return False
        for member_model in members_queue:
            if member_model.member == member:
                return False
        # Add member to the lobby
        lobby.members_queue.append(MemberModel(member))
        return True

    @classmethod
    def remove_member(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        member: discord.Member
    ) -> bool:
        lobby = cls.get_lobby(bot, lobby_id)
        members = lobby.members
        members_queue = lobby.members_queue
        # Check if member is in the lobby
        for member_model in members:
            if member_model.member.id == member.id:
                members.remove(member_model)
                return True
        for member_model in members_queue:
            if member_model.member.id == member.id:
                members_queue.remove(member_model)
                return True
        return False

    @classmethod
    async def move_queue_members(cls, bot: LobbyBot, lobby_id: int) -> None:
        lobby = cls.get_lobby(bot, lobby_id)
        members = lobby.members
        members_queue = lobby.members_queue
        members_length = len(members_queue)
        if members_length != 0:
            for _ in range(members_length):
                members.append(members_queue.pop(0))
        if len(members_queue) == 0:
            # Remove this if there are too many updates.
            lobby.queue_embed = None
            queue_message = LobbyManager.get_queue_embed_message(bot, lobby_id)
            if queue_message is not None:
                await queue_message.delete()
                lobby.queue_message = None

    @classmethod
    def update_member_state(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        member: discord.Member
    ) -> MemberState:
        for member_model in cls.get_lobby( bot, lobby_id).members:
            if member_model.member == member:
                member_state = member_model.update()
                return member_state

    @classmethod
    def lock(cls, bot: LobbyBot, lobby_id: int) -> LobbyState:
        lobby = cls.get_lobby(bot, lobby_id)
        status = lobby.status

        if status == LobbyState.UNLOCK:
            new_status = LobbyState.LOCK
        elif status == LobbyState.LOCK:
            new_status = LobbyState.UNLOCK
        lobby.status = new_status
        return new_status

    @classmethod
    def has_joined(cls, bot: LobbyBot, lobby_id: int, member: discord.Member) -> bool:
        for member_model in cls.get_lobby(bot, lobby_id).members:
            if member_model.member.id == member.id:
                return True
        return False

    @classmethod
    def switch_owner(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        member: discord.Member
    ) -> None:
        '''Swap a member with the owner of the lobby'''
        # Check if the member is in the lobby
        has_joined = cls.has_joined(bot, lobby_id, member)

        if has_joined and member != cls.get_lobby_owner(bot, lobby_id):
            lobby = cls.get_lobby(bot, lobby_id)
            lobby.owner = member
            member_list = lobby.members
            for index, member_model in enumerate(member_list):
                if member_model.member == member:
                    new_owner = lobby.members.pop(index)
                    old_owner = lobby.members.pop(0)
                    lobby.members.insert(0, new_owner)
                    lobby.members.append(old_owner)
                    break

    @classmethod
    def search_new_owner(cls, bot: LobbyBot, lobby_id: int) -> bool:
        '''Choose the next owner in lobby and move next owner up to first slot'''

        lobby = cls.get_lobby(bot, lobby_id)
        # Check if there is no other member in the lobby
        if len(lobby.members) == 1:
            return False

        # Get the next owner
        new_owner = lobby.members[1].member
        lobby.owner = new_owner.member
        lobby.members[0], lobby.members[1] = \
            lobby.members[1], lobby.members[0]
        return True

    @classmethod
    def remove_owner(cls, bot: LobbyBot, lobby_id: int) -> None:
        # Check if there is no other member in the lobby
        lobby = cls.get_lobby(bot, lobby_id)
        if len(lobby.members) == 1:
            return False

        # Get the next owner
        new_owner = lobby.members[1].member
        lobby.owner = new_owner
        lobby.members.pop(0)
        return True

    @classmethod
    def get_member_length(cls, bot: LobbyBot, lobby_id: int) -> int:
        '''Get the number of members in the lobby'''
        return len(cls.get_lobby(bot, lobby_id).members)

    @classmethod
    def get_members_ready(cls, bot: LobbyBot, lobby_id: int) -> list[discord.Member]:
        '''Get the number of members that are ready'''
        members = [member_model.member for member_model in cls.get_lobby(bot, lobby_id)
                   .members if member_model.state == MemberState.READY]
        return members

    @classmethod
    def get_members_not_ready(cls, bot: LobbyBot, lobby_id: int) -> list[discord.Member]:
        '''Get the number of members that are not ready'''
        members = [member_model.member for member_model in cls.get_lobby(bot, lobby_id).members
                   if member_model.state == MemberState.NOT_READY]
        return members

    @classmethod
    def get_lobby_lock(cls, bot: LobbyBot, lobby_id: int) -> LobbyState:
        '''Get the lock state of the lobby'''
        return cls.get_lobby(bot, lobby_id).status

    @classmethod
    async def delete_lobby(cls, bot: LobbyBot, lobby_id: int) -> None:
        lobby = cls.get_lobby(bot, lobby_id)
        # Delete channel
        channel = lobby.lobby_channel
        await channel.delete()
        # Delete lobby data
        bot.lobby.pop(lobby_id)

    @classmethod
    def set_descriptor(cls, bot: LobbyBot, lobby_id: int, description: str) -> None:
        '''Set the description of the lobby'''
        cls.get_lobby(bot, lobby_id).description = description

    @classmethod
    def get_descriptor(cls, bot: LobbyBot, lobby_id: int) -> str | None:
        '''Get the description of the lobby'''
        return cls.get_lobby(bot, lobby_id).description

    @classmethod
    def is_full(cls, bot: LobbyBot, lobby_id: int) -> bool:
        '''Check if the lobby is full'''
        lobby = cls.get_lobby(bot, lobby_id)
        if int(lobby.game_size) == lobby.members:
            return True
        else:
            return False

    @classmethod
    def get_session_time(cls, bot: LobbyBot, lobby_id: int) -> str:
        '''Get the session time of the lobby'''
        creation: datetime = cls.get_lobby(bot, lobby_id).created_datetime
        deletion = datetime.now()
        duration = deletion - creation
        return "Session Duration: " + strftime("%H:%M:%S", gmtime(duration.total_seconds()))

    @classmethod
    def get_last_promotion_message(cls, bot: LobbyBot, lobby_id: int) -> discord.Message | None:
        '''Get the last promotion message'''
        return cls.get_lobby(bot, lobby_id).last_promotion_message

    @classmethod
    def can_promote(cls, bot: LobbyBot, lobby_id: int) -> bool:
        '''Check if last promotion message is older than 10 minutes'''
        lobby = cls.get_lobby(bot, lobby_id)
        if lobby.last_promotion_message is None:
            return True
        else:
            last_promotion_datetime = lobby.last_promotion_datetime
            if last_promotion_datetime is None or (datetime.now() - last_promotion_datetime) > timedelta(minutes=10):
                return True
            else:
                return False

    @classmethod
    def set_last_promotion_message(
        cls,
        bot: LobbyBot,
        lobby_id: int,
        message: discord.Message
    ) -> None:
        '''Set the last promotion message'''
        lobby = cls.get_lobby(bot, lobby_id)
        lobby.last_promotion_message = message
        lobby.last_promotion_datetime = datetime.now()

    @classmethod
    def get_unready_mentions(cls, bot: LobbyBot, lobby_id: int) -> str:
        members_to_ping = cls.get_members_not_ready(bot, lobby_id)
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @classmethod
    def get_ready_mentions(cls, bot: LobbyBot, lobby_id: int) -> str:
        members_to_ping = cls.get_members_ready(bot, lobby_id)
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @classmethod
    def get_new_owner_mention(cls, bot: LobbyBot, lobby_id: int) -> str:
        return f'<@{cls.get_lobby_owner(bot, lobby_id).id}>'
