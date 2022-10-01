from datetime import datetime
from enum import Enum
import discord
from discord.ext import commands

from model.lobby_model import LobbyManager, LobbyState


class LobbyEmbed(discord.Embed):
    def __init__(
        self,
        lobby_id: int,
        bot: commands.Bot,
    ):
        # Setup slots and owner field
        super().__init__(description='No description set')
        self.lobby_id = lobby_id
        self.bot = bot
        self.color = discord.Color.red()
        self.type

    async def update(self):
        # Reset embed
        self.clear_fields()
        # Populate embed
        self._set_author()
        self._set_descriptor()
        self._set_colour()
        self._fill_closed_slots()
        self._fill_open_slots()
        self._set_footer()
        # Send embed
        embed_message = LobbyManager.get_embed_message(self.bot, self.lobby_id)
        if embed_message is not None:
            await embed_message.edit(embed=self)

    def _set_author(self) -> None:
        owner = LobbyManager.get_lobby_owner(self.bot, self.lobby_id)
        self.set_author(
            name=f"👑 Lobby Owner: {owner.display_name}", icon_url=owner.display_avatar.url
        )

    def _set_descriptor(self) -> None:
        discriptor = LobbyManager.get_descriptor(self.bot, self.lobby_id)
        if discriptor is not None:
            self.description = f'Description: {discriptor}'
        else:
            self.description = 'No description set'

    def _set_colour(self) -> None:
        lobby_state = LobbyManager.get_lobby_status(self.bot, self.lobby_id)
        if lobby_state == LobbyState.LOCKED:
            self.color = discord.Color.yellow()
        elif LobbyManager.is_full(self.bot, self.lobby_id):
            self.color = discord.Color.green()
        else:
            self.color = discord.Color.red()

    def _set_footer(self) -> None:
        game_size = LobbyManager.get_gamesize(self.bot, self.lobby_id)
        lobby_length = LobbyManager.get_member_length(self.bot, self.lobby_id)
        member_ready = len(LobbyManager.get_members_ready(self.bot, self.lobby_id))
        footer = f'🎮 {lobby_length}/{game_size} slots filled, {member_ready}/{game_size} ready'
        self.set_footer(text=footer)

    def _fill_closed_slots(self) -> None:
        members = LobbyManager.get_members(self.bot, self.lobby_id)

        # Update fields base on lobby model
        for member_model in members:
            self.add_field(
                name=member_model.member.display_name,
                value=f'Status: {member_model.state.value[0]}',
                inline=False
            )

    def _fill_open_slots(self) -> None:
        game_size = LobbyManager.get_gamesize(self.bot, self.lobby_id)
        lobby_length = LobbyManager.get_member_length(self.bot, self.lobby_id)

        if lobby_length < int(game_size):
            for _ in range(int(game_size) - lobby_length):
                self.add_field(
                    name='Empty',
                    value='😩 Fill me daddy',
                    inline=False
                )


class UpdateMessageEmbedColour(Enum):
    LEAVE = discord.Color.red()
    JOIN = discord.Color.blue()
    READY = discord.Color.green()
    OWNER_CHANGE = discord.Color.blurple()
    DESCRIPTION_CHANGE = discord.Color.blurple()
    SIZE_CHANGE = discord.Color.blurple()
    GAME_CHANGE = discord.Color.blurple()
    LOCK = discord.Color.yellow()
    UNLOCK = discord.Color.blue()
    DELETE = discord.Color.red()


class UpdateMessageEmbedMessage(Enum):
    LEAVE = 'left the lobby!'
    JOIN = 'joined the lobby!'
    READY = 'is ready!'
    OWNER_CHANGE = 'has taken over the lobby!'
    DESCRIPTION_CHANGE = 'has changed the description to'
    SIZE_CHANGE = 'has changed the game size to'
    GAME_CHANGE = 'has changed the game to'
    LOCK = 'has locked the lobby!'
    UNLOCKED = 'has unlocked the lobby!'
    DELETE = 'has deleted the lobby!'


class UpdateMessageEmbedType(Enum):
    LEAVE = 'LEAVE'
    JOIN = 'JOIN'
    READY = 'READY'
    OWNER_CHANGE = 'OWNER CHANGED'
    DESCRIPTION_CHANGE = 'DESCRIPTION CHANGED'
    SIZE_CHANGE = 'SIZE CHANGED'
    GAME_CHANGE = 'GAME CHANGED'
    LOCK = 'LOCKED'
    UNLOCKED = 'UNLOCKED'
    DELETE = 'DELETED'


class UpdateMessageEmbed(discord.Embed):
    def __init__(
            self,
            bot: commands.Bot,
            lobby_id: int,
            member: discord.Member,
            embed_type: UpdateMessageEmbedType
    ):
        super().__init__()
        self.payload = {
            UpdateMessageEmbedType.LEAVE.value: {
                'colour': UpdateMessageEmbedColour.LEAVE.value,
                'message': UpdateMessageEmbedMessage.LEAVE.value
            },
            UpdateMessageEmbedType.JOIN.value: {
                'colour': UpdateMessageEmbedColour.JOIN.value,
                'message': UpdateMessageEmbedMessage.JOIN.value
            },
            UpdateMessageEmbedType.READY.value: {
                'colour': UpdateMessageEmbedColour.READY.value,
                'message': UpdateMessageEmbedMessage.READY.value
            },
            UpdateMessageEmbedType.OWNER_CHANGE.value: {
                'colour': UpdateMessageEmbedColour.OWNER_CHANGE.value,
                'message': UpdateMessageEmbedMessage.OWNER_CHANGE.value
            },
            UpdateMessageEmbedType.DESCRIPTION_CHANGE.value: {
                'colour': UpdateMessageEmbedColour.DESCRIPTION_CHANGE.value,
                'message': UpdateMessageEmbedMessage.DESCRIPTION_CHANGE.value
            },
            UpdateMessageEmbedType.SIZE_CHANGE.value: {
                'colour': UpdateMessageEmbedColour.SIZE_CHANGE.value,
                'message': UpdateMessageEmbedMessage.SIZE_CHANGE.value
            },
            UpdateMessageEmbedType.GAME_CHANGE.value: {
                'colour': UpdateMessageEmbedColour.GAME_CHANGE.value,
                'message': UpdateMessageEmbedMessage.GAME_CHANGE.value
            },
            UpdateMessageEmbedType.LOCK.value: {
                'colour': UpdateMessageEmbedColour.LOCK.value,
                'message': UpdateMessageEmbedMessage.LOCK.value
            },
            UpdateMessageEmbedType.UNLOCKED.value: {
                'colour': UpdateMessageEmbedColour.UNLOCK.value,
                'message': UpdateMessageEmbedMessage.UNLOCKED.value
            },
            UpdateMessageEmbedType.DELETE.value: {
                'colour': UpdateMessageEmbedColour.DELETE.value,
                'message': UpdateMessageEmbedMessage.DELETE.value
            }
        }

        self.set_author(name=bot.user.display_name, icon_url=bot.user.display_avatar.url)
        self._set_descriptor(bot, lobby_id, embed_type)
        self._set_fields(member, bot, lobby_id, embed_type)
        if embed_type == UpdateMessageEmbedType.READY:
            members = LobbyManager.get_members_not_ready(bot, lobby_id)
            if len(members) != 0:
                self.add_field(
                    name='Please get ready:',
                    value=', '.join(f'<@{member.id}>' for member in members),
                    inline=False
                )
        self.color = self.payload[embed_type.value]['colour']
        self.set_footer(
            text=f"⌚ {datetime.now().strftime('%I:%M:%S%p')}"
        )

    def _set_descriptor(self, bot, lobby_id, embed_type) -> None:
        if embed_type == UpdateMessageEmbedType.DELETE:
            return
        descriptor = LobbyManager.get_descriptor(bot, lobby_id)
        mention = LobbyManager.get_channel(bot, lobby_id).id
        if descriptor and embed_type != UpdateMessageEmbedType.DESCRIPTION_CHANGE:
            self.description = f'Description: {descriptor}, <#{mention}>'
        else:
            self.description = f'<#{mention}>'

    def _set_fields(
        self,
        member: discord.Member,
        bot: commands.Bot,
        lobby_id: int,
        embed_type: UpdateMessageEmbedType
    ) -> None:
        extra = self.get_additional_fields(embed_type, lobby_id, bot)
        message = f"{self.payload[embed_type.value]['message']}"

        if extra is not None:
            message += f' {extra}.'

        # Change name if there is an owner change.
        name = None
        if embed_type == UpdateMessageEmbedType.OWNER_CHANGE:
            name = LobbyManager.get_lobby_owner(bot, lobby_id).display_name
        else:
            name = member.display_name

        self.add_field(
            name=name,
            value=message,
        )

    def get_additional_fields(
        self,
        embed_type: UpdateMessageEmbedType,
        lobby_id: int,
        bot: commands.Bot
    ) -> str:
        if embed_type == UpdateMessageEmbedType.GAME_CHANGE:
            return LobbyManager.get_gamecode(bot, lobby_id)
        elif embed_type == UpdateMessageEmbedType.SIZE_CHANGE:
            return LobbyManager.get_gamesize(bot, lobby_id)
        elif embed_type == UpdateMessageEmbedType.DESCRIPTION_CHANGE:
            return LobbyManager.get_descriptor(bot, lobby_id)
