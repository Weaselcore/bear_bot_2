from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from discord.ext import commands
from view.lobby.button_view import ClosedSlotButtonView, OpenSlotButtonView

import discord


class MemberState(Enum):
    NOT_READY = 'not ready',
    READY = 'ready',

    def __str__(self):
        return f'{ self.value[0].upper()}'


class LobbyState(Enum):
    LOCKED = 'locked',
    UNLOCKED = 'unlocked',

    def __str__(self):
        return f'{ self.value[0].upper()}'


@dataclass
class MemberModel:
    member: discord.Member
    join_datetime = datetime.now()
    state = MemberState.NOT_READY


class ClosedSlotEmbed(discord.Embed):
    def __init__(
            self,
            member: discord.Member,
            datetime: datetime,
            id=0
    ):
        super().__init__()
        self.id = id
        self.member = member
        self.datetime = datetime
        self.set_author(name=member.name, icon_url=member.display_avatar.url)
        self.add_field(
            name='Filled',
            value='Not Ready'
        )
        self.fields
        self.set_footer(text=f'⌚ Joined at {datetime.strftime("%X")}')
        self.colour = discord.Colour.red()

    async def update(self, embed_message: discord.Message, member_state: MemberState):
        if member_state == MemberState.NOT_READY:
            self.color = discord.Color.red()
            msg = "🛑 Unreadied at"
            self.set_field_at(0, name='Filled', value='Not Ready')
        elif member_state == MemberState.READY:
            self.color = discord.Color.green()
            msg = "✔ Readied at"
            self.set_field_at(0, name='Filled', value='Ready')

        self.set_footer(text=f'{msg} {self.datetime.now().strftime("%X")}')
        await embed_message.edit(embed=self)

    async def set_lock(self, embed_message: discord.Message, lobby_state: LobbyState):
        msg = ""
        if lobby_state == LobbyState.LOCKED:
            self.color = discord.Color.yellow()
            msg = "🔒 Locked at"
            self.set_field_at(0, name='Filled', value='Locked')
        elif lobby_state == LobbyState.UNLOCKED:
            self.color = discord.Color.green()
            msg = "🔓 Unlocked at"
            self.set_field_at(0, name='Filled', value='Ready')
        self.set_footer(text=f'{msg} {self.datetime.now().strftime("%X")}')
        await embed_message.edit(embed=self)


class OpenSlotEmbed(discord.Embed):
    def __init__(self, index: int):
        super().__init__()
        self.id = index
        self.add_field(name='Open Slot', value="Click join to fill")
        self.color = discord.Color.blue()

    async def set_lock(self, embed_message: discord.Message, lobby_state: LobbyState):
        msg = ""
        if lobby_state == LobbyState.LOCKED:
            self.color = discord.Color.yellow()
            msg = "🔒 Locked at"
            self.set_field_at(0, name='Open Slot', value='Locked')
        elif lobby_state == LobbyState.UNLOCKED:
            self.color = discord.Color.blue()
            msg = "🔓 Unlocked at"
            self.set_field_at(0, name='Open Slot', value='Click join to fill')
        self.set_footer(text=f'{msg} {datetime.now().strftime("%X")}')
        await embed_message.edit(embed=self)


class UpdateEmbed(discord.Embed):
    def __init__(
            self, title: str,
            value: str,
            color: discord.Color,
            footer=None,
            descriptor=None

    ):
        super().__init__()
        self.add_field(name=title, value=value)
        if descriptor is not None:
            self.add_field(name='Description', value=descriptor)
        self.color = color
        self.set_footer(text=footer)


@dataclass
class EmbedModel:
    index: int
    embed: ClosedSlotEmbed | OpenSlotEmbed
    embed_message: discord.Message
    member_model: MemberModel = None

    async def update(self):
        # if type(self.embed) is OpenSlotEmbed:
        await self.embed.update(self.embed_message, self.member_model.state)


@dataclass
class LobbyModel:
    # Use the message id as the lobby id
    owner: discord.User
    original_channel: discord.TextChannel
    lobby_channel: discord.TextChannel
    thread: discord.Thread
    control_panel_message: discord.Message
    description: str = None
    embeds = {}
    status = LobbyState.UNLOCKED
    game_code = 'gametype'
    game_size = 'gamesize'

    def __str__(self):
        return f'Owner        : {self.owner}\n'\
            f'Embed        : {self.embeds}\n'\
            f'Og_channel_id: {self.original_channel}\n'\
            f'Lobby        : {self.lobby_channel}\n'\
            f'Thread       : {self.thread}\n'\
            f'Game_code    : {self.game_code}\n'\
            f'Game_size    : {self.game_size}\n'


class LobbyManager:

    @staticmethod
    def get_lobby(bot: commands.Bot, lobby_id: int) -> LobbyModel:
        return bot.lobby[lobby_id]

    @staticmethod
    def set_lobby(bot: commands.Bot, lobby_id: int, lobby: LobbyModel) -> None:
        bot.lobby[lobby_id] = lobby

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
    def get_lobby_name(bot: commands.Bot, lobby_id: int) -> str:
        return f'{bot.lobby[lobby_id].game_code} - {bot.lobby[lobby_id].game_size}'

    @staticmethod
    def get_lobby_id(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].lobby_channel

    @staticmethod
    def get_lobby_owner(bot: commands.Bot, lobby_id: int) -> discord.User:
        return bot.lobby[lobby_id].owner

    @staticmethod
    def print_lobby(bot: commands.Bot, lobby_id: int) -> None:
        print(bot.lobby[lobby_id])

    @staticmethod
    def get_lobby_status(bot: commands.Bot, lobby_id: int) -> LobbyState:
        return bot.lobby[lobby_id].status

    @staticmethod
    def update_lobby_status(bot: commands.Bot, lobby_id: int) -> LobbyModel:
        status = bot.lobby[lobby_id].status
        if status == LobbyState.UNLOCKED:
            bot.lobby[lobby_id].lock()
        else:
            bot.lobby[lobby_id].unlock()

    @staticmethod
    def get_thread(bot: commands.Bot, lobby_id: int) -> discord.Thread:
        return bot.lobby[lobby_id].thread

    @staticmethod
    def get_channel(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].lobby_channel

    @staticmethod
    def get_original_channel(bot: commands.Bot, lobby_id: int) -> discord.TextChannel:
        return bot.lobby[lobby_id].original_channel

    @staticmethod
    def add_slot(
        bot: commands.Bot,
        lobby_id: int,
        embed: discord.Embed,
        index: int,
        embed_message: discord.Message,
    ) -> None:
        bot.lobby[lobby_id].embeds[index] = EmbedModel(index, embed, embed_message)

    @staticmethod
    async def update_embed(bot: commands.Bot, lobby_id: int, index: int) -> None:
        await bot.lobby[lobby_id].embeds[index].update()

    @staticmethod
    def get_embed(bot: commands.Bot, lobby_id: int, index: int) -> discord.Embed:
        return bot.lobby[lobby_id].embeds[index]

    @staticmethod
    async def fill_open_embed(
        bot: commands.Bot,
        lobby_id: int,
        index: int,
        member: discord.User
    ) -> None:
        try:
            if bot.lobby[lobby_id].embeds[index].member_model is None:
                bot.lobby[lobby_id].embeds[index].embed = ClosedSlotEmbed(
                    member=member,
                    datetime=datetime.now(),
                    id=index
                )
                bot.lobby[lobby_id].embeds[index].member_model = MemberModel(member)
                await bot.lobby[lobby_id].embeds[index].embed_message.edit(
                    embed=bot.lobby[lobby_id].embeds[index].embed,
                    view=ClosedSlotButtonView(index, lobby_id, bot)
                )
        except KeyError:
            raise KeyError('EmbedModel does not exist')

    @staticmethod
    async def clear_closed_embed(
        bot: commands.Bot,
        lobby_id: int,
        index: int
    ) -> None:
        if bot.lobby[lobby_id].embeds[index].member_model is not None:
            bot.lobby[lobby_id].embeds[index].embed = OpenSlotEmbed(
                index=index
            )
            bot.lobby[lobby_id].embeds[index].member_model = None
            await bot.lobby[lobby_id].embeds[index].embed_message.edit(
                embed=bot.lobby[lobby_id].embeds[index].embed,
                view=OpenSlotButtonView(index, lobby_id, bot)
            )

    @staticmethod
    def get_member(bot: commands.Bot, lobby_id: int, index: int) -> discord.User:
        return bot.lobby[lobby_id].embeds[index].member_model.member

    @staticmethod
    def add_member(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.User,
        index: int
    ) -> bool | None:
        # Check if member is in lobby data
        if bot.lobby[lobby_id].embeds[index].member_model is None:
            # Add member data to lobby data
            bot.lobby[lobby_id].embeds[index].member_model = MemberModel(member)
            return True
        else:
            return None

    @staticmethod
    def update_member_state(
        bot: commands.Bot,
        lobby_id: int,
        member: discord.User,
        state: MemberState,
        index: int
    ) -> None:
        bot.dispatch(
            'log_history',
            lobby_id,
            f'{member.name} has changed their state to {state}'
        )
        bot.lobby[lobby_id].embeds[index].member_model.state = state

    @staticmethod
    async def lock(bot: commands.Bot, lobby_id: int) -> None:
        if bot.lobby[lobby_id].status == LobbyState.UNLOCKED:
            new_status = LobbyState.LOCKED
        elif bot.lobby[lobby_id].status == LobbyState.LOCKED:
            new_status = LobbyState.UNLOCKED
        bot.lobby[lobby_id].status = new_status
        for embed_model in bot.lobby[lobby_id].embeds.values():
            embed_message = embed_model.embed_message
            await embed_model.embed.set_lock(embed_message, new_status)

    @staticmethod
    def has_joined(bot: commands.Bot, lobby_id: int, member: discord.User) -> bool:
        for embed_model in bot.lobby[lobby_id].embeds.values():
            if embed_model.member_model is not None and \
                    embed_model.member_model.member.id == member.id:
                return True
        return False

    @staticmethod
    async def switch_owner(bot: commands.Bot, lobby_id: int, index: int) -> None:
        '''Swap a member with the owner of the lobby'''
        old_owner = bot.lobby[lobby_id].owner
        bot.lobby[lobby_id].owner = bot.lobby[lobby_id].embeds[index].member_model.member

        # Move old owner embed
        bot.lobby[lobby_id].embeds[index].member_model = MemberModel(old_owner)
        bot.lobby[lobby_id].embeds[index].embed = ClosedSlotEmbed(old_owner, datetime.now(), index)
        # Move new owner embed
        bot.lobby[lobby_id].embeds[0].member_model = MemberModel(bot.lobby[lobby_id].owner)
        bot.lobby[lobby_id].embeds[0].embed = ClosedSlotEmbed(
            bot.lobby[lobby_id].owner,
            datetime.now(),
            0
        )
        await bot.lobby[lobby_id].embeds[index].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[index].embed,
        )

        await bot.lobby[lobby_id].embeds[0].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[0].embed,
        )

    @staticmethod
    async def search_new_owner(bot: commands.Bot, lobby_id: int) -> bool:
        '''Choose the next owner in lobby and move next owner up to first slot'''

        found_member_index = None
        # Find next filled spot
        for index in bot.lobby[lobby_id].embeds:
            if bot.lobby[lobby_id].embeds[index].member_model is not None and \
                    bot.lobby[lobby_id].embeds[index] != bot.lobby[lobby_id].embeds[0]:
                found_member_index = index
                break
        else:
            return False

        old_owner = bot.lobby[lobby_id].owner
        bot.lobby[lobby_id].owner = bot.lobby[lobby_id]\
            .embeds[found_member_index].member_model.member

        # Move new owner embed
        bot.lobby[lobby_id].embeds[0].member_model = MemberModel(bot.lobby[lobby_id].owner)
        bot.lobby[lobby_id].embeds[0].embed = ClosedSlotEmbed(
            bot.lobby[lobby_id].owner,
            datetime.now(),
            0
        )
        # Update embed to show new owner in new embed
        await bot.lobby[lobby_id].embeds[0].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[0].embed
        )

        # Move old owner embed
        bot.lobby[lobby_id].embeds[found_member_index].member_model = MemberModel(old_owner)
        bot.lobby[lobby_id].embeds[found_member_index].embed = ClosedSlotEmbed(
            old_owner,
            datetime.now(),
            found_member_index
        )
        await bot.lobby[lobby_id].embeds[found_member_index].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[found_member_index].embed
        )
        return True

    @staticmethod
    async def remove_owner(bot: commands.Bot, lobby_id: int) -> None:
        found_member_index = None
        # Find next filled spot
        for index in bot.lobby[lobby_id].embeds:
            if bot.lobby[lobby_id].embeds[index].member_model is not None and \
                    bot.lobby[lobby_id].embeds[index] != bot.lobby[lobby_id].embeds[0]:
                found_member_index = index
                break
        else:
            return
        '''Remove the owner from the lobby'''
        bot.lobby[lobby_id].owner = bot.lobby[lobby_id]\
            .embeds[found_member_index].member_model.member

        # Move new owner embed
        bot.lobby[lobby_id].embeds[0].member_model = MemberModel(bot.lobby[lobby_id].owner)
        bot.lobby[lobby_id].embeds[0].embed = ClosedSlotEmbed(
            bot.lobby[lobby_id].owner,
            datetime.now(),
            0
        )
        # Update embed to show new owner in new embed
        await bot.lobby[lobby_id].embeds[0].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[0].embed
        )

        # Move old owner embed
        bot.lobby[lobby_id].embeds[found_member_index].member_model = None
        bot.lobby[lobby_id].embeds[found_member_index].embed = OpenSlotEmbed(index)
        await bot.lobby[lobby_id].embeds[found_member_index].embed_message.edit(
            embed=bot.lobby[lobby_id].embeds[found_member_index].embed,
            view=OpenSlotButtonView(found_member_index, lobby_id, bot)
        )

    @staticmethod
    def get_member_length(bot: commands.Bot, lobby_id: int) -> int:
        '''Get the number of members in the lobby'''
        count = 0
        for embed_model in bot.lobby[lobby_id].embeds.values():
            if embed_model.member_model is not None:
                count += 1
        return count

    @staticmethod
    async def delete_lobby(bot: commands.Bot, lobby_id: int) -> None:
        lobby_data = bot.lobby[lobby_id]
        # Delete thread
        thread = lobby_data.thread
        await thread.delete()
        # Delete channel
        channel = lobby_data.lobby_channel
        await channel.delete()
        # Delete lobby data
        bot.lobby.pop(lobby_id)

    @staticmethod
    async def resize_lobby(bot: commands.Bot, lobby_id: int) -> None:
        '''Resize the lobby to a new size'''
        game_size = int(bot.lobby[lobby_id].game_size)
        lobby_data_size = len(bot.lobby[lobby_id].embeds)
        if game_size > lobby_data_size:
            # Add embeds
            for index in range(0, game_size - lobby_data_size):
                embed_message = await bot.lobby[lobby_id].lobby_channel.send(
                    embed=OpenSlotEmbed(lobby_data_size + index - 1),
                    view=OpenSlotButtonView(lobby_data_size + index - 1, lobby_id, bot)
                )
                bot.lobby[lobby_id].embeds[lobby_data_size + index - 1] = EmbedModel(
                    game_size + index - 1,
                    OpenSlotEmbed(lobby_data_size + index - 1),
                    embed_message,
                    None
                )
        else:
            # Remove embeds
            list_of_message = []
            for index in range(0, lobby_data_size - game_size):
                embed_model = bot.lobby[lobby_id].embeds.pop(lobby_data_size - index - 1)
                list_of_message.append(embed_model.embed_message)
            await bot.lobby[lobby_id].lobby_channel.delete_messages(list_of_message)

    @staticmethod
    def set_descriptor(bot: commands.Bot, lobby_id: int, description: str) -> None:
        '''Set the description of the lobby'''
        bot.lobby[lobby_id].description = description
        bot.dispatch(
            "log_history",
            lobby_id,
            f"Description set to '{description}'"
        )

    @staticmethod
    def get_descriptor(bot: commands.Bot, lobby_id: int) -> str:
        '''Get the description of the lobby'''
        return bot.lobby[lobby_id].description
