from datetime import datetime
from enum import Enum
from typing import Any, Protocol, TypeVar
import discord
import pytz
from discord.ext import commands

# This prevents circular imports
import model.lobby_model as lobby_model


class LobbyModel(Protocol):
    control_panel: discord.Message
    lobby_channel: discord.TextChannel
    original_channel: discord.TextChannel
    owner: discord.Member
    created_datetime: datetime
    description: str | None
    embed_message: discord.Message | None
    queue_message: discord.Message | None
    game_code: str
    game_size: int
    last_promotion_message: discord.Message | None = None
    last_promotion_datetime: datetime | None = None
    is_promoting = False
    thread: discord.Thread | None = None


class LobbyEmbed(discord.Embed):
    def __init__(
        self,
        lobby_id: int,
        bot: Any,
    ):
        # Setup slots and owner field
        super().__init__(description='No description set')
        self.lobby_id = lobby_id
        self.bot = bot
        self.color = discord.Color.red() # type: ignore
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
        embed_message = lobby_model.LobbyManager.get_embed_message(self.bot, self.lobby_id)
        if embed_message is not None:
            await embed_message.edit(embed=self)

    def _set_author(self) -> None:
        owner = lobby_model.LobbyManager.get_lobby_owner(self.bot, self.lobby_id)
        self.set_author(
            name=f"👑 Lobby Owner: {owner.display_name}", icon_url=owner.display_avatar.url
        )

    def _set_descriptor(self) -> None:
        discriptor = lobby_model.LobbyManager.get_descriptor(self.bot, self.lobby_id)
        if discriptor is not None:
            self.description = f'Description: {discriptor}'
        else:
            self.description = 'No description set'

    def _set_colour(self) -> None:
        lobby_state = lobby_model.LobbyManager.get_lobby_status(self.bot, self.lobby_id)
        if lobby_state == lobby_model.LobbyState.LOCK:
            self.color = discord.Color.yellow()
        elif lobby_model.LobbyManager.is_full(self.bot, self.lobby_id):
            self.color = discord.Color.green()
        else:
            self.color = discord.Color.red()

    def _set_footer(self) -> None:
        game_size = lobby_model.LobbyManager.get_gamesize(self.bot, self.lobby_id)
        lobby_length = lobby_model.LobbyManager.get_member_length(self.bot, self.lobby_id)
        member_ready = len(lobby_model.LobbyManager.get_members_ready(self.bot, self.lobby_id))
        footer = f'🎮 {lobby_length}/{game_size} slots filled, {member_ready}/{game_size} ready'
        self.set_footer(text=footer)

    def _fill_closed_slots(self) -> None:
        members = lobby_model.LobbyManager.get_members(self.bot, self.lobby_id)

        # Update fields base on lobby model
        for member_model in members:
            self.add_field(
                name=member_model.member.display_name,
                value=f'Status: {member_model.state.value[0]}',
                inline=False
            )

    def _fill_open_slots(self) -> None:
        game_size = lobby_model.LobbyManager.get_gamesize(self.bot, self.lobby_id)
        lobby_length = lobby_model.LobbyManager.get_member_length(self.bot, self.lobby_id)

        if lobby_length < int(game_size):
            for _ in range(int(game_size) - lobby_length):
                self.add_field(
                    name='Empty',
                    value='😩 Fill me daddy',
                    inline=False
                )


class QueueEmbed(discord.Embed):
    def __init__(self, bot: Any, lobby_id: int):
        super().__init__(description='Members in queue')
        self.bot = bot
        self.lobby_id = lobby_id
        self.color = discord.Color.yellow()

    async def update(self):
        # Reset embed
        self.clear_fields()
        # Populate embed
        self._set_slots()
        # Send embed
        queue_embed_message = lobby_model.LobbyManager.get_queue_embed_message(self.bot, self.lobby_id)
        if queue_embed_message is not None:
            await queue_embed_message.edit(embed=self)

    def _set_slots(self):
        queued_members = lobby_model.LobbyManager.get_queue_members(self.bot, self.lobby_id)
        for count, member_model in enumerate(queued_members):
            self.add_field(
                name=f'#{count + 1}',
                value=member_model.member.display_name,
                inline=False
            )


class UpdateEmbedType(Enum):
    LEAVE = 'LEAVE'
    JOIN = 'JOIN'
    READY = 'READY'
    OWNER_CHANGE = 'OWNER_CHANGE'
    DESCRIPTION_CHANGE = 'DESCRIPTION_CHANGE'
    SIZE_CHANGE = 'SIZE_CHANGE'
    GAME_CHANGE = 'GAME_CHANGE'
    LOCK = 'LOCK'
    UNLOCK = 'UNLOCK'
    DELETE = 'DELETE'


class UpdateEmbedColour(Enum):
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


class UpdateEmbedMessage(Enum):
    LEAVE = 'has left the lobby! 💨'
    JOIN = 'has joined the lobby! 🏃‍♂️'
    READY = 'is ready! 🟢'
    OWNER_CHANGE = 'has changed the lobby owner to'
    DESCRIPTION_CHANGE = 'has changed the lobby description to'
    SIZE_CHANGE = 'has changed the lobby size to'
    GAME_CHANGE = 'has changed the lobby game to'
    LOCK = 'has locked the lobby! 🔒'
    UNLOCK = 'has unlocked the lobby! 🔓'
    DELETE = 'has deleted the lobby! 🛑'


class UpdateEmbedManager:

    @staticmethod
    def get_message_details( #noqa
        bot: Any,
        lobby_id: int,
        embed_type: UpdateEmbedType,
        member: discord.Member | discord.User = None
    ) -> tuple[str| None, discord.Embed]:

        def _set_footer(embed: discord.Embed) -> discord.Embed:
            timezone = pytz.timezone('Pacific/Auckland')
            date_time = datetime.now()
            localised_date_time = date_time.astimezone(tz=timezone)
            embed.set_footer(
                text=f"⌚ {localised_date_time.strftime('%I:%M:%S%p')}"
            )
            return embed

        def _get_embed(
            lobby_id: int,
            bot: Any,
            embed_type: UpdateEmbedType
        ) -> discord.Embed:

            if embed_type == UpdateEmbedType.OWNER_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                    description=lobby_model.LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +
                    ' ' +
                    lobby_model.LobbyManager.get_lobby_owner(bot, lobby_id).display_name,
                )
            elif embed_type == UpdateEmbedType.DESCRIPTION_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +
                    ' ' +
                    lobby_model.LobbyManager.get_descriptor(bot, lobby_id),
                )
            elif embed_type == UpdateEmbedType.SIZE_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                    description=lobby_model.LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +
                    ' ' +
                    lobby_model.LobbyManager.get_gamesize(bot, lobby_id),
                )
            elif embed_type == UpdateEmbedType.GAME_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                    description=lobby_model.LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +
                    ' ' +
                    lobby_model.LobbyManager.get_gamecode(bot, lobby_id),
                )
            elif embed_type == UpdateEmbedType.DELETE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                    description=lobby_model.LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value,
                ).set_footer(
                    text=lobby_model.LobbyManager.get_session_time(bot, lobby_id)
                )
                return embed
            else:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,
                    description=lobby_model.LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value,
                )
            return _set_footer(embed)

        def _get_ping(lobby_id: int, bot: commands.Bot, embed_type: UpdateEmbedType) -> str | None:
            if embed_type == UpdateEmbedType.LOCK:
                return lobby_model.LobbyManager.get_ready_mentions(bot, lobby_id)
            elif embed_type == UpdateEmbedType.OWNER_CHANGE:
                return lobby_model.LobbyManager.get_new_owner_mention(bot, lobby_id)
            elif embed_type == UpdateEmbedType.READY:
                return (lobby_model.LobbyManager.get_unready_mentions(bot, lobby_id) +
                        lobby_model.LobbyManager.get_new_owner_mention(bot, lobby_id))
            else:
                return None

        return (_get_ping(lobby_id, bot, embed_type), _get_embed(lobby_id, bot, embed_type))
