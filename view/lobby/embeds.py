from datetime import datetime
from enum import Enum
from typing import Optional
import discord
import pytz
from discord import Color

from stubs import Client
from model.lobby.lobby_model import LobbyManager, LobbyState


class LobbyEmbed(discord.Embed):
    def __init__(
            self,
            lobby_id: int,
            bot: Client,
    ):
        # Setup slots and owner field
        super().__init__(description='No description set')
        self.lobby_id = lobby_id
        self.bot = bot
        self.color: Color = discord.Color.red()  # type: ignore

    async def update(self) -> None:
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
        if lobby_state == LobbyState.LOCK:
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
    def get_message_details(
            bot: Client,
            lobby_id: int,
            embed_type: UpdateEmbedType,
            member: discord.Member
    ) -> tuple[Optional[str], discord.Embed]:

        def _set_footer(embed: discord.Embed) -> discord.Embed:
            timezone = pytz.timezone('Pacific/Auckland')
            date_time = datetime.now()
            localised_date_time = date_time.astimezone(tz=timezone)
            embed.set_footer(
                text=f"⌚ {localised_date_time.strftime('%I:%M:%S%p')}"
            )
            return embed

        def _get_embed() -> discord.Embed:

            if embed_type == UpdateEmbedType.OWNER_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                    description=LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +  # type: ignore
                          ' ' + LobbyManager.get_lobby_owner(bot, lobby_id).display_name,
                )
            elif embed_type == UpdateEmbedType.DESCRIPTION_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +  # type: ignore
                          ' ' +
                          LobbyManager.get_descriptor(bot, lobby_id),
                )
            elif embed_type == UpdateEmbedType.SIZE_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                    description=LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +  # type: ignore
                          ' ' +
                          str(LobbyManager.get_gamesize(bot, lobby_id)),
                )
            elif embed_type == UpdateEmbedType.GAME_CHANGE:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                    description=LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value +  # type: ignore
                          ' ' +
                          LobbyManager.get_gamecode(bot, lobby_id),
                )
            elif embed_type == UpdateEmbedType.DELETE:
                embed = discord.Embed(  # type: ignore
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                    description=LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value,  # type: ignore
                ).set_footer(
                    text=LobbyManager.get_session_time(bot, lobby_id)
                )
                return embed
            else:
                embed = discord.Embed(
                    color=UpdateEmbedColour[embed_type.value].value,  # type: ignore
                    description=LobbyManager.get_descriptor(bot, lobby_id)
                ).add_field(
                    name=member.display_name,
                    value=UpdateEmbedMessage[embed_type.value].value,  # type: ignore
                )
            return _set_footer(embed)

        def _get_ping() -> str | None:
            result = None
            if embed_type == UpdateEmbedType.LOCK:
                result = LobbyManager.get_ready_mentions(bot, lobby_id)
            elif embed_type == UpdateEmbedType.OWNER_CHANGE:
                result = LobbyManager.get_new_owner_mention(bot, lobby_id)
            elif embed_type == UpdateEmbedType.READY:
                get_unready = LobbyManager.get_unready_mentions(bot, lobby_id)
                get_owner = LobbyManager.get_new_owner_mention(bot, lobby_id)
                if get_unready is None:
                    result = get_owner
                else:
                    result = get_owner + get_unready
            return result

        return _get_ping(), _get_embed()
