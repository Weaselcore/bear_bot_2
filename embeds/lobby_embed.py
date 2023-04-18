from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from discord import (
    Color,
    Embed,
    Member,
    Message,
    PartialMessage,
    TextChannel,
    Thread,
    User, 
)
from discord.ui import View


class UpdateEmbedType(Enum):
    LEAVE = 'LEAVE'
    JOIN = 'JOIN'
    READY = 'READY'
    DESCRIPTION_CHANGE = 'DESCRIPTION_CHANGE'
    SIZE_CHANGE = 'SIZE_CHANGE'
    GAME_CHANGE = 'GAME_CHANGE'
    LOCK = 'LOCK'
    UNLOCK = 'UNLOCK'
    DELETE = 'DELETE'
    OWNER_CHANGE = 'OWNER_CHANGE'
    OWNER_ADD = 'OWNER_ADD'
    OWNER_REMOVE = 'OWNER_REMOVE'
    OWNER_READY = 'OWNER_READY'
    CLEAN_UP = 'CLEAN_UP'


class UpdateEmbedColour(Enum):
    LEAVE = Color.red()
    JOIN = Color.blue()
    READY = Color.green()
    OWNER_CHANGE = Color.blurple()
    DESCRIPTION_CHANGE = Color.blurple()
    SIZE_CHANGE = Color.blurple()
    GAME_CHANGE = Color.blurple()
    LOCK = Color.yellow()
    UNLOCK = Color.blue()
    DELETE = Color.red()
    OWNER_ADD = Color.blue()
    OWNER_REMOVE = Color.red()
    OWNER_READY = Color.green()
    CLEAN_UP = Color.red()


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
    DELETE = 'has deleted their lobby! 🛑'
    OWNER_ADD = 'has added someone to the lobby! 🏃‍♂️ :'
    OWNER_REMOVE = 'has removed someone from the lobby! 💨 :'
    OWNER_READY = "has updated someone's status! ℹ :"
    CLEAN_UP = 'has cleaned up lobby'


class LobbyEmbed(Embed):
    def __init__(
        self,
        lobby_id: int,
        owner: Member | User,
        description: str | None,
        is_locked: bool,
        is_full: bool,
        members: list[Member],
        member_ready: Sequence[int],
        game_size: int,

    ):
        # Setup slots and owner field
        super().__init__(
            description='Description: None',
        )

        self.set_author(
            name=f"👑 Lobby Owner: {owner.display_name}",
            icon_url=owner.display_avatar.url
        )

        # Set description
        if description is not None:
            self.description = f'```Description: {description}```'
        else:
            self.description = 'Description: None'

        # Set colour based on status
        if is_locked:
            self.color = Color.yellow()  # type: ignore
        elif is_full:
            self.color = Color.green()  # type: ignore
        else:
            self.color = Color.red()  # type: ignore

        # Fill in closed slots with status message.
        for member in members:
            self.add_field(
                name=member.display_name,
                value=f'⠀⠀⤷ **Status**: \
            {"Ready" if member.id in member_ready else "Not Ready"}',
                inline=False
            )

        # Fill in open slots
        lobby_length = len(members)
        if lobby_length < int(game_size):
            for _ in range(int(game_size) - lobby_length):
                self.add_field(
                    name='Empty',
                    value='⠀⠀⤷ 😩 Fill me daddy',
                    inline=False
                )

        # Add footer with lobby id and fill/ready status.
        footer = f'[Lobby ID:  {lobby_id}] [🎮 {lobby_length}/{game_size} slots filled, \
    ✅ {len(member_ready)}/{game_size} ready]'
        self.set_footer(text=footer)


class QueueEmbed(Embed):
    def __init__(self, queue_members: list[Member]):
        super().__init__(
            description='Queue',
            color=Color.yellow()
        )

        for count, member in enumerate(queue_members):
            self.add_field(
                name=f'#{count + 1} Member',
                value=member.display_name,
                inline=False
            )


class LobbyEmbedManager:

    UPDATE_TYPES = UpdateEmbedType

    @staticmethod
    async def send_update_embed(
        update_type: UpdateEmbedType,
        title: str,
        destination: TextChannel | Thread,
        additional_string: str | None = None,
        footer_string: str | None = None,
        pings: str | None = None,
    ) -> None:

        message = None
        default_footer = True
        new_field = False

        match update_type:
            case UpdateEmbedType.JOIN:
                message = UpdateEmbedMessage.JOIN.value
            case UpdateEmbedType.LEAVE:
                message = UpdateEmbedMessage.LEAVE.value
            case UpdateEmbedType.READY:
                message = UpdateEmbedMessage.READY.value
            case UpdateEmbedType.OWNER_CHANGE:
                message = f'{UpdateEmbedMessage.OWNER_CHANGE.value} {additional_string}'
            case UpdateEmbedType.DESCRIPTION_CHANGE:
                message = f'{UpdateEmbedMessage.DESCRIPTION_CHANGE.value} \
                    **{additional_string}**'
            case UpdateEmbedType.SIZE_CHANGE:
                message = f'{UpdateEmbedMessage.SIZE_CHANGE.value} {additional_string}'
            case UpdateEmbedType.GAME_CHANGE:
                message = f'{UpdateEmbedMessage.GAME_CHANGE.value} {additional_string}'
            case UpdateEmbedType.LOCK:
                message = UpdateEmbedMessage.LOCK.value
            case UpdateEmbedType.UNLOCK:
                message = UpdateEmbedMessage.UNLOCK.value
            case UpdateEmbedType.DELETE:
                message = UpdateEmbedMessage.DELETE.value
                default_footer = False
                if additional_string != "" or additional_string is not None:
                    new_field = True
            case UpdateEmbedType.OWNER_ADD:
                message = f'{UpdateEmbedMessage.OWNER_ADD.value} {additional_string}'
            case UpdateEmbedType.OWNER_REMOVE:
                message = f'{UpdateEmbedMessage.OWNER_REMOVE.value} {additional_string}'
            case UpdateEmbedType.OWNER_READY:
                message = f'{UpdateEmbedMessage.OWNER_READY.value} {additional_string}'
            case UpdateEmbedType.CLEAN_UP:
                message = f'{UpdateEmbedMessage.CLEAN_UP.value} {additional_string}! 🧹'
                default_footer = False
            case _:
                raise NotImplementedError

        embed = Embed(
            title=title,
            description=message,
            color=UpdateEmbedColour[update_type.value].value
        )

        # Set footer with current time
        if default_footer:
            embed.timestamp = datetime.now()
        #     embed.set_footer(
        #         text="⌚ {utils.format_dt(datetime.utcnow(), 'T')}"
        #     )
        else:
            embed.set_footer(text=footer_string)

        # Add new field if needed
        if new_field:
            embed.add_field(
                name='Reason:',
                value=additional_string,
                inline=False
            )

        await destination.send(content=pings, embed=embed)

    @staticmethod
    async def create_lobby_embed(
        lobby_id: int,
        owner: Member | User,
        description: str | None,
        is_locked: bool,
        is_full: bool,
        members: list[Member],
        member_ready: list[int],
        game_size: int,
        channel: TextChannel | Thread,
        view: View
    ) -> int | None:

        embed = LobbyEmbed(
            lobby_id=lobby_id,
            owner=owner,
            description=description,
            is_locked=is_locked,
            is_full=is_full,
            members=members,
            member_ready=member_ready,
            game_size=game_size,
        )

        lobby_message = await channel.send(embed=embed, view=view)
        return lobby_message.id

    @staticmethod
    async def update_lobby_embed(
        lobby_id: int,
        owner: Member | User,
        description: str | None,
        is_locked: bool,
        is_full: bool,
        members: list[Member],
        member_ready: Sequence[int],
        game_size: int,
        message: Message | PartialMessage |  None,
    ) -> None:

        if description is None:
            description = 'No description provided.'

        embed = LobbyEmbed(
            lobby_id=lobby_id,
            owner=owner,
            description=description,
            is_locked=is_locked,
            is_full=is_full,
            members=members,
            member_ready=member_ready,
            game_size=game_size,
        )
        if message is not None:
            await message.edit(embed=embed)

    @staticmethod
    async def create_queue_embed(
        queue_members: list[Member],
        channel: TextChannel | Thread,
    ) -> int | None:
        queue_embed = QueueEmbed(queue_members)
        queue_message = await channel.send(embed=queue_embed)
        return queue_message.id

    @staticmethod
    async def update_queue_embed(
        queue_members: list[Member],
        message: Message | PartialMessage | None,
    ) -> None:
        queue_embed = QueueEmbed(queue_members)
        if message is not None:
            await message.edit(embed=queue_embed)
