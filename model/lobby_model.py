from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from time import gmtime, strftime
from discord.ext import commands
import discord


class MemberState(Enum):
    NOT_READY = 'Not Ready',
    READY = 'Ready',

    def __str__(self):
        return f'{ self.value[0].upper()}'


class LobbyState(Enum):
    LOCK = 'locked',
    UNLOCK = 'unlocked',

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
    description: str = None
    embed: discord.Embed = None
    embed_message: discord.Message = None
    game_code = 'gametype'
    game_size = 1
    last_promotion_message: discord.Message = None
    last_promotion_datetime: datetime = None
    is_promoting = False
    members: list[MemberModel] = field(default_factory=list)
    thread: discord.Thread = None
    status = LobbyState.UNLOCK


class LobbyManager:

    @staticmethod
    def get_lobby(bot: commands.Bot, lobby_id: int) -> LobbyModel:
        return bot.lobby[lobby_id]

    @staticmethod
    def set_lobby(bot: commands.Bot, lobby_id: int, lobby: LobbyModel) -> None:
        bot.lobby[lobby_id] = lobby

    @staticmethod
    def get_thread(bot: commands.Bot, lobby_id: int) -> discord.Thread:
        return bot.lobby[lobby_id].thread

    @staticmethod
    def set_thread(bot: commands.Bot, lobby_id: int, thread: discord.Thread) -> None:
        bot.lobby[lobby_id].thread = thread

    @staticmethod
    def get_gamecode(bot: commands.Bot, lobby_id: int) -> str:
        return bot.lobby[lobby_id].game_code

    @staticmethod
    def set_gamecode(bot: commands.Bot, lobby_id: int, game_code: str) -> LobbyModel:
        bot.lobby[lobby_id].game_code = game_code
        return bot.lobby[lobby_id]

    @staticmethod
    def get_gamesize(bot: commands.Bot, lobby_id: int) -> str:
        return bot.lobby[lobby_id].game_size

    @staticmethod
    def set_gamesize(bot: commands.Bot, lobby_id: int, game_size: str) -> LobbyModel:
        bot.lobby[lobby_id].game_size = game_size
        return bot.lobby[lobby_id]

    @staticmethod
    def get_lobby_name(bot: commands.Bot) -> str:
        lobby_number = len(bot.lobby)
        return f'Lobby {lobby_number}'

    @staticmethod
    def get_lobby_id(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].lobby_channel

    @staticmethod
    def get_lobby_owner(bot: commands.Bot, lobby_id: int) -> discord.Member:
        return bot.lobby[lobby_id].owner

    @staticmethod
    def print_lobby(bot: commands.Bot, lobby_id: int) -> None:
        print(bot.lobby[lobby_id])

    @staticmethod
    def get_lobby_status(bot: commands.Bot, lobby_id: int) -> LobbyState:
        return bot.lobby[lobby_id].status

    @staticmethod
    def update_lobby_status(bot: commands.Bot, lobby_id: int) -> LobbyModel:
        lobby_model = bot.lobby[lobby_id]

        if lobby_model.status == LobbyState.UNLOCK:
            lobby_model.status = LobbyState.LOCK
        else:
            lobby_model.status = LobbyState.UNLOCK

    @staticmethod
    def get_channel(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].lobby_channel

    @staticmethod
    def get_original_channel(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].original_channel

    @staticmethod
    async def update_control_panel(bot: commands.Bot, lobby_id: int) -> None:
        await bot.lobby[lobby_id].control_panel.update()

    @staticmethod
    def get_control_panel(bot: commands.Bot, lobby_id: int) -> discord.Embed | None:
        return bot.lobby[lobby_id].control_panel

    @staticmethod
    def get_embed_message(bot: commands.Bot, lobby_id: int) -> discord.Embed | None:
        return bot.lobby[lobby_id].embed_message

    @staticmethod
    def set_embed_message(bot: commands.Bot, lobby_id: int, embed_message: discord.Embed) -> None:
        bot.lobby[lobby_id].embed_message = embed_message

    @staticmethod
    def get_embed(bot: commands.Bot, lobby_id: int) -> discord.Embed | None:
        return bot.lobby[lobby_id].embed

    @staticmethod
    def set_embed(bot: commands.Bot, lobby_id: int, embed: discord.Embed) -> None:
        bot.lobby[lobby_id].embed = embed

    @staticmethod
    def get_members(bot: commands.Bot, lobby_id: int) -> list[MemberModel]:
        return bot.lobby[lobby_id].members

    @staticmethod
    def add_member(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.Member
    ) -> bool:
        members = bot.lobby[lobby_id].members
        # Check if member is in the lobby
        for member_model in members:
            if member_model.member == member:
                return False
        # Add member to the lobby
        bot.lobby[lobby_id].members.append(MemberModel(member))
        return True

    @staticmethod
    def remove_member(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.Member
    ) -> bool:
        members = bot.lobby[lobby_id].members
        # Check if member is in the lobby
        for member_model in members:
            if member_model.member.id == member.id:
                members.remove(member_model)
                return True
        return False

    @staticmethod
    def update_member_state(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.Member
    ) -> MemberState:
        for member_model in bot.lobby[lobby_id].members:
            if member_model.member == member:
                member_state = member_model.update()
                return member_state

    @staticmethod
    def lock(bot: commands.Bot, lobby_id: int) -> LobbyState:
        if bot.lobby[lobby_id].status == LobbyState.UNLOCK:
            new_status = LobbyState.LOCK
        elif bot.lobby[lobby_id].status == LobbyState.LOCK:
            new_status = LobbyState.UNLOCK
        bot.lobby[lobby_id].status = new_status
        return new_status

    @staticmethod
    def has_joined(bot: commands.Bot, lobby_id: int, member: discord.Member) -> bool:
        for member_model in bot.lobby[lobby_id].members:
            if member_model.member.id == member.id:
                return True
        return False

    @staticmethod
    def switch_owner(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.Member
    ) -> None:
        '''Swap a member with the owner of the lobby'''
        # Check if the member is in the lobby
        has_joined = LobbyManager.has_joined(bot, lobby_id, member)

        if has_joined and member != LobbyManager.get_lobby_owner(bot, lobby_id):
            bot.lobby[lobby_id].owner = member
            member_list = bot.lobby[lobby_id].members
            for index, member_model in enumerate(member_list):
                if member_model.member == member:
                    new_owner = bot.lobby[lobby_id].members.pop(index)
                    old_owner = bot.lobby[lobby_id].members.pop(0)
                    bot.lobby[lobby_id].members.insert(0, new_owner)
                    bot.lobby[lobby_id].members.append(old_owner)
                    break

    @staticmethod
    def search_new_owner(bot: commands.Bot, lobby_id: int) -> bool:
        '''Choose the next owner in lobby and move next owner up to first slot'''

        # Check if there is no other member in the lobby
        if len(bot.lobby[lobby_id].members) == 1:
            return False

        # Get the next owner
        new_owner = bot.lobby[lobby_id].members[1].member
        bot.lobby[lobby_id].owner = new_owner.member
        bot.lobby[lobby_id].members[0], bot.lobby[lobby_id].members[1] = \
            bot.lobby[lobby_id].members[1], bot.lobby[lobby_id].members[0]
        return True

    @staticmethod
    def remove_owner(bot: commands.Bot, lobby_id: int) -> None:
        # Check if there is no other member in the lobby
        if len(bot.lobby[lobby_id].members) == 1:
            return False

        # Get the next owner
        new_owner = bot.lobby[lobby_id].members[1].member
        bot.lobby[lobby_id].owner = new_owner
        bot.lobby[lobby_id].members.pop(0)
        return True

    @staticmethod
    def get_member_length(bot: commands.Bot, lobby_id: int) -> int:
        '''Get the number of members in the lobby'''
        return len(bot.lobby[lobby_id].members)

    @staticmethod
    def get_members_ready(bot: commands.Bot, lobby_id: int) -> list[discord.Member]:
        '''Get the number of members that are ready'''
        members = [member_model.member for member_model in bot.lobby[lobby_id]
                   .members if member_model.state == MemberState.READY]
        return members

    @staticmethod
    def get_members_not_ready(bot: commands.Bot, lobby_id: int) -> list[discord.Member]:
        '''Get the number of members that are not ready'''
        members = [member_model.member for member_model in bot.lobby[lobby_id].members
                   if member_model.state == MemberState.NOT_READY]
        return members

    @staticmethod
    def get_lobby_lock(bot: commands.Bot, lobby_id: int) -> LobbyState:
        '''Get the lock state of the lobby'''
        return bot.lobby[lobby_id].status

    @staticmethod
    async def delete_lobby(bot: commands.Bot, lobby_id: int) -> None:
        lobby_data = bot.lobby[lobby_id]
        # Delete channel
        channel = lobby_data.lobby_channel
        await channel.delete()
        # Delete lobby data
        bot.lobby.pop(lobby_id)

    @staticmethod
    def set_descriptor(bot: commands.Bot, lobby_id: int, description: str) -> None:
        '''Set the description of the lobby'''
        bot.lobby[lobby_id].description = description

    @staticmethod
    def get_descriptor(bot: commands.Bot, lobby_id: int) -> str | None:
        '''Get the description of the lobby'''
        return bot.lobby[lobby_id].description

    @staticmethod
    def is_full(bot: commands.Bot, lobby_id: int) -> bool:
        '''Check if the lobby is full'''
        if int(bot.lobby[lobby_id].game_size) == len(bot.lobby[lobby_id].members):
            return True
        else:
            return False

    @staticmethod
    def get_session_time(bot: commands.Bot, lobby_id: int) -> str:
        '''Get the session time of the lobby'''
        creation: datetime = bot.lobby[lobby_id].created_datetime
        deletion = datetime.now()
        duration = deletion - creation
        return "Session Duration: " + strftime("%H:%M:%S", gmtime(duration.total_seconds()))

    @staticmethod
    def get_last_promotion_message(bot: commands.Bot, lobby_id: int) -> discord.Message | None:
        '''Get the last promotion message'''
        return bot.lobby[lobby_id].last_promotion_message

    @staticmethod
    def set_last_promotion_message(
        bot: commands.Bot,
        lobby_id: int,
        message: discord.Message
    ) -> None:
        '''Set the last promotion message'''
        bot.lobby[lobby_id].last_promotion_message = message

    @staticmethod
    def get_unready_mentions(bot: commands.Bot, lobby_id: int) -> str:
        members_to_ping = LobbyManager.get_members_not_ready(bot, lobby_id)
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @staticmethod
    def get_ready_mentions(bot: commands.Bot, lobby_id: int) -> str:
        members_to_ping = LobbyManager.get_members_ready(bot, lobby_id)
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    @staticmethod
    def get_new_owner_mention(bot: commands.Bot, lobby_id: int) -> str:
        return f'<@{LobbyManager.get_lobby_owner(bot, lobby_id).id}>'
