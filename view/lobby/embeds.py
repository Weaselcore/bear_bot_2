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


class UpdateMessageEmbedColour(Enum):
    LEAVE = discord.Color.red()
    JOIN = discord.Color.blue()
    READY = discord.Color.green()
    OWNER_CHANGE = discord.Color.blurple()
    DESCRIPTION_CHANGE = discord.Color.blurple()
    SIZE_CHANGE = discord.Color.blurple()
    GAME_CHANGE = discord.Color.blurple()
    LOCK = discord.Color.yellow()
    UNLOCKED = discord.Color.blue()
    DELETE = discord.Color.red()


class UpdateEmbedManager:

    @staticmethod
    def get_message_details( #noqa
        bot: commands.Bot,
        lobby_id: int,
        embed_type: UpdateMessageEmbedType,
        member: discord.Member = None
    ) -> set[list | None, discord.Embed]:

        def _set_footer(embed: discord.Embed) -> discord.Embed:
            timezone = pytz.timezone('Pacific/Auckland')
            date_time = datetime.now()
            localised_date_time = date_time.astimezone(tz=timezone)
            embed.set_footer(
                text=f"⌚ {localised_date_time.strftime('%I:%M:%S%p')}"
            )
            return embed

        def _get_unready_mentions(bot: commands.Bot, lobby_id: int) -> str:
            members_to_ping = LobbyManager.get_members_not_ready(bot, lobby_id)
            mention_list = [f'<@{member.id}>' for member in members_to_ping]
            return ", ".join(mention_list)

        def _get_ready_mentions(bot: commands.Bot, lobby_id: int) -> str:
            members_to_ping = LobbyManager.get_members_ready(bot, lobby_id)
            mention_list = [f'<@{member.id}>' for member in members_to_ping]
            return ", ".join(mention_list)

        def _get_new_owner_mention(bot: commands.Bot, lobby_id: int) -> str:
            return f'<@{LobbyManager.get_lobby_owner(bot, lobby_id).id}>'

        if embed_type == UpdateMessageEmbedType.READY:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.READY.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='is ready!'
            )
            return (_get_unready_mentions(bot, lobby_id), _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.JOIN:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.JOIN.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='has joined the lobby!'
            )
            return (None, _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.LEAVE:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.LEAVE.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='has left the lobby!'
            )
            return (None, _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.DELETE:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.DELETE.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='has shut the door behind them, lobby closed! 🛑'
            ).set_footer(
                text=f'Session Duration: {LobbyManager.get_session_time(bot, lobby_id)}'
            )
            return (None, embed)
        elif embed_type == UpdateMessageEmbedType.GAME_CHANGE:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.GAME_CHANGE.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value=f'has changed the game to {LobbyManager.get_gamecode(bot, lobby_id)}!'
            )
            return (None, _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.OWNER_CHANGE:
            new_owner = LobbyManager.get_lobby_owner(bot, lobby_id).display_name
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.OWNER_CHANGE.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=new_owner,
                value='is now the new owner! 👑'
            )
            return (_get_new_owner_mention(bot, lobby_id), _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.SIZE_CHANGE:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.SIZE_CHANGE.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value=f'has changed the size to {LobbyManager.get_gamesize(bot, lobby_id)}!'
            )
            return (None, _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.DESCRIPTION_CHANGE:
            new_description = LobbyManager.get_descriptor(bot, lobby_id)
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.DESCRIPTION_CHANGE.value,
            ).add_field(
                name=member.display_name,
                value=f'has changed the description to {new_description}!'
            )
            return (None, _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.LOCK:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.LOCK.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='has locked the lobby! 🔒'
            )
            return (_get_ready_mentions(bot, lobby_id), _set_footer(embed))
        elif embed_type == UpdateMessageEmbedType.UNLOCKED:
            embed = discord.Embed(
                color=UpdateMessageEmbedColour.UNLOCKED.value,
                description=LobbyManager.get_descriptor(bot, lobby_id)
            ).add_field(
                name=member.display_name,
                value='has unlocked the lobby! 🔓'
            )
            return (None, _set_footer(embed))
