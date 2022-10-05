from datetime import datetime
from enum import Enum
import discord
import pytz
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
                'colour': discord.Color.red(),
                'message': 'left the lobby!'
            },
            UpdateMessageEmbedType.JOIN.value: {
                'colour': discord.Color.blue(),
                'message': 'joined the lobby!'
            },
            UpdateMessageEmbedType.READY.value: {
                'colour': discord.Color.green(),
                'message': 'is ready!'
            },
            UpdateMessageEmbedType.OWNER_CHANGE.value: {
                'colour': discord.Color.blurple(),
                'message': 'has taken over the lobby!'
            },
            UpdateMessageEmbedType.DESCRIPTION_CHANGE.value: {
                'colour': discord.Color.blurple(),
                'message': 'has changed the description to'
            },
            UpdateMessageEmbedType.SIZE_CHANGE.value: {
                'colour': discord.Color.blurple(),
                'message': 'has changed the game size to'
            },
            UpdateMessageEmbedType.GAME_CHANGE.value: {
                'colour': discord.Color.blurple(),
                'message': 'has changed the game to'
            },
            UpdateMessageEmbedType.LOCK.value: {
                'colour': discord.Color.yellow(),
                'message': 'has locked the lobby!'
            },
            UpdateMessageEmbedType.UNLOCKED.value: {
                'colour': discord.Color.blue(),
                'message': 'has unlocked the lobby!'
            },
            UpdateMessageEmbedType.DELETE.value: {
                'colour': discord.Color.red(),
                'message': 'has shut the door behind them, lobby closed! 🛑'
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
        self._set_footer()

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
        extra = self._get_additional_fields(embed_type, lobby_id, bot)
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

    def _get_additional_fields(
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

    def _set_footer(self):
        timezone = pytz.timezone('Pacific/Auckland')
        date_time = datetime.now()
        localised_date_time = date_time.astimezone(tz=timezone)
        self.set_footer(
            text=f"⌚ {localised_date_time.strftime('%I:%M:%S%p')}"
        )
