from datetime import datetime, timedelta
from datetime import UTC as UTC
from typing import TypeVar, Union
from zoneinfo import ZoneInfo

import discord

from api.lobby_api import LobbyApi
from api.models import (
    GameModel,
    InsertGameModel,
    InsertLobbyModel,
    LobbyModel,
    LobbyStates,
    MemberLobbyModel,
    MemberModel,
    MessageResponseModel,
)
from cog.classes.lobby.lobby_cache import LobbyCache
from cog.classes.lobby.transformer_cache import TransformerCache
from cog.classes.utils import set_logger
from embeds.lobby_embed import LobbyEmbedManager
from exceptions.lobby_exceptions import DeletedLobby, LobbyNotFound, MemberNotFound, ThreadChannelNotFound

T = TypeVar(
    "T",
    GameModel,
    LobbyModel,
    MemberModel,
)
U = TypeVar(
    "U",
    tuple[GameModel, MessageResponseModel],
    tuple[LobbyModel, MessageResponseModel],
    tuple[MemberModel, MessageResponseModel],
)


class LobbyManager:
    def __init__(
        self,
        api_manager: LobbyApi,
        bot: discord.Client,
        embed_manager: LobbyEmbedManager,
        transformer_cache: TransformerCache,
        lobby_cache: LobbyCache,
    ) -> None:
        self._api_manager = api_manager
        self.bot = bot
        self.embed_manager = embed_manager
        self.logger = set_logger("lobby_manager")
        self.transformer_cache = transformer_cache
        self.lobby_cache = lobby_cache

    """Cache Retrieval Functions"""

    async def _get_guild(self, guild_id: int) -> discord.Guild:
        guild_from_cache = self.bot.get_guild(guild_id)
        if guild_from_cache:
            return guild_from_cache
        guild = await self.bot.fetch_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")
        return guild

    async def get_thread(self, guild_id: int, thread_id: int) -> discord.Thread:
        guild = await self._get_guild(guild_id)

        history_thread_from_cache = guild.get_thread(thread_id)
        if history_thread_from_cache:
            return history_thread_from_cache

        history_thread = await guild.fetch_channel(thread_id)
        if not history_thread:
            raise ValueError("History thread not found")
        if isinstance(history_thread, discord.Thread):
            return history_thread
        raise TypeError("Channel is not a thread.")

    async def get_channel(self, guild_id: int, channel_id: int) -> discord.TextChannel:
        guild = await self._get_guild(guild_id)

        lobby_channel_from_cache = guild.get_channel(channel_id)
        if lobby_channel_from_cache:
            assert isinstance(lobby_channel_from_cache, discord.TextChannel)
            return lobby_channel_from_cache

        lobby_channel_from_fetch = await guild.fetch_channel(channel_id)
        if not lobby_channel_from_fetch:
            raise ValueError("Lobby channel not found")
        return lobby_channel_from_fetch  # type: ignore

    async def get_message(
        self, guild_id: int, channel_id: int, message_id: int
    ) -> discord.Message | discord.PartialMessage:

        channel = await self.get_channel(guild_id, channel_id)
        assert channel

        control_panel_message_from_cache = channel.get_partial_message(message_id)
        if control_panel_message_from_cache:
            return control_panel_message_from_cache

        message_from_fetch = await channel.fetch_message(message_id)
        if not message_from_fetch:
            raise ValueError("Control panel message not found")
        return message_from_fetch

    async def get_member(self, guild_id: int, member_id: int) -> discord.Member:
        guild = await self._get_guild(guild_id)

        member_from_cache = guild.get_member(member_id)
        if member_from_cache:
            return member_from_cache

        member_from_fetch = await guild.fetch_member(member_id)
        if member_from_fetch:
            return member_from_fetch

        raise MemberNotFound(member_id)

    """Fetch Functions"""

    async def get_all_lobbies(self) -> list[LobbyModel]:

        @self.lobby_cache
        async def _get_all_lobbies(self):
            lobbies, _ = await self._api_manager.get_lobbies()
            return lobbies

        lobbies = await _get_all_lobbies(self)
        return lobbies

    async def get_lobby(self, lobby_id: int) -> LobbyModel:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        return lobby

    async def get_lobby_by_owner_id(self, owner_id: int) -> LobbyModel:
        lobby, _ = await self._api_manager.get_lobby_by_owner_id(owner_id)
        return lobby

    async def get_guild_id(self, lobby_id: int) -> int:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        return lobby.guild_id

    async def get_games_by_guild_id(self, guild_id: int) -> list[GameModel] | None:

        @self.transformer_cache
        async def _get_games_by_guild_id(self, guild_id: int) -> list[GameModel] | None:
            games, _ = await self._api_manager.get_games_by_guild_id(guild_id)
            if games is None:
                return None
            return games

        return await _get_games_by_guild_id(self, guild_id)

    async def get_game(self, game_id: int) -> GameModel:
        game, _ = await self._api_manager.get_game(game_id)
        return game

    async def get_members(self, lobby: LobbyModel) -> list[discord.Member]:
        list_of_members = [
            await self.get_member(lobby.guild_id, member.member_id)
            for member in lobby.member_lobbies
        ]
        final_list = list(filter(None, list_of_members))
        return final_list

    async def get_queue_members(self, lobby_id: int) -> list[discord.Member]:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        list_of_queue_members = [
            await self.get_member(lobby.guild_id, member.member_id)
            for member in lobby.queue_member_lobbies
        ]
        final_list = list(filter(None, list_of_queue_members))
        return final_list

    async def get_members_status(
        self, lobby_id: int, ready_status: bool
    ) -> list[MemberLobbyModel]:
        """Get the number of members that are ready"""
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        return [
            member for member in lobby.member_lobbies if member.ready == ready_status
        ]

    async def get_session_time(self, created_datetime: datetime) -> str:
        """Get the session time of the lobby"""

        # Database stores UTC datetime strings but with the timezone data truncated.
        localised_creation_datetime = datetime.fromtimestamp(
            created_datetime.timestamp(), UTC
        )
        localised_datetime_now = datetime.now(UTC)

        duration = localised_datetime_now - localised_creation_datetime

        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        # Format the duration as a string
        duration_str = "{:02}:{:02}:{:02}".format(hours, minutes, seconds)

        return "Session Duration: " + duration_str

    async def get_ready_mentions(self, lobby_id: int) -> str:
        members_to_ping = await self.get_members_status(lobby_id, True)
        mention_list = [f"<@{member}>" for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_owner_mention(self, lobby_id: int) -> str:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        return f"<@{(await self.get_member(lobby.guild_id, lobby.owner_id)).id}>"

    """Create Functions"""

    async def create_lobby(
        self,
        original_channel_id: int,
        guild_id: int,
        guild_name: str,
        owner_id: int,
        game_id: int,
        max_size: int,
        description: str,
    ) -> LobbyModel:

        @self.lobby_cache
        async def _create_lobby(
            self,
            original_channel_id: int,
            guild_id: int,
            guild_name: str,
            owner_id: int,
            game_id: int,
            max_size: int,
            description: str,
        ) -> LobbyModel:
            lobby, _ = await self._api_manager.post_lobby(
                InsertLobbyModel(
                    original_channel_id=original_channel_id,
                    guild_id=guild_id,
                    guild_name=guild_name,
                    owner_id=owner_id,
                    game_id=game_id,
                    game_size=max_size,
                    description=description,
                )
            )
            return lobby

        return await _create_lobby(
            self,
            original_channel_id=original_channel_id,
            guild_id=guild_id,
            guild_name=guild_name,
            owner_id=owner_id,
            game_id=game_id,
            max_size=max_size,
            description=description,
        )

    async def create_game(
        self,
        guild_id: int,
        game_name: str,
        max_size: int,
        role_id: int | None,
        icon_url: str | None,
    ) -> GameModel:

        @self.transformer_cache
        async def _create_game(
            self,
            guild_id: int,
            game_name: str,
            max_size: int,
            role_id: int | None,
            icon_url: str | None,
        ) -> GameModel:
            game_model, _ = await self._api_manager.post_game(
                InsertGameModel(
                    name=game_name,
                    guild_id=guild_id,
                    max_size=max_size,
                    role=role_id,
                    icon_url=icon_url,
                )
            )
            return game_model

        return await _create_game(
            self, guild_id, game_name, max_size, role_id, icon_url
        )

    async def add_member(
        self, lobby_id: int, member_id: int, owner_added: bool = False
    ) -> None:
        lobby = await self.get_lobby(lobby_id)
        await self._api_manager.post_member(lobby.id, MemberModel(id=member_id))

        if lobby.history_thread_id is None:
            raise ThreadChannelNotFound

        member = await self.get_member(lobby.guild_id, member_id)
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        if not owner_added:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.JOIN,
                title=member.display_name,
                destination=thread,
            )
        elif owner_added:
            owner = await self.get_member(lobby.guild_id, lobby.owner_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_ADD,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
            )

    """Update Functions"""

    async def _update_model_instance(
        self,
        instance: Union[GameModel, LobbyModel, MemberModel],
        lobby_id=None,
    ) -> Union[
        tuple[GameModel, MessageResponseModel],
        tuple[LobbyModel, MessageResponseModel],
        tuple[MemberModel, MessageResponseModel],
    ]:
        # Determine the appropriate function based on the instance type
        if isinstance(instance, LobbyModel):
            result = await self._api_manager.put_lobby(instance)
            self.lobby_cache.set(str(result[0].id), result[0]) # type: ignore
            return result
        elif isinstance(instance, MemberModel):
            return await self._api_manager.put_member(lobby_id, instance)
        elif isinstance(instance, GameModel):
            result = await self._api_manager.put_game(instance)
            self.transformer_cache.set(str(result[0].id), result[0]) # type: ignore
            return result
        else:
            self.logger.warning(f"No specific handler found for {instance.__str__}.")
            raise NotImplementedError

    async def update_lobby(self, lobby: LobbyModel) -> LobbyModel:
        lobby, _ = await self._update_model_instance(lobby)
        return lobby

    async def update_game_id(self, lobby_id: int, game_id: int) -> int:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        lobby.game_id = game_id
        await self._update_model_instance(lobby)

        owner = await self.get_member(lobby.guild_id, lobby.owner_id)

        try:
            assert lobby.history_thread_id is not None
            thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.GAME_CHANGE,
                title=owner.display_name,
                destination=thread,
                additional_string=str(lobby.game_id),
            )
        except Exception:
            pass
        return lobby.game_id

    async def update_gamesize(self, lobby_id: int, game_size: int) -> int:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        lobby.game_size = game_size
        await self._update_model_instance(lobby)
        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        try:
            if not isinstance(lobby.history_thread_id, int):
                raise TypeError("History Thread ID not set.")
            thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.GAME_CHANGE,
                title=owner.display_name,
                destination=thread,
                additional_string=str(game_size),
            )
        except Exception:
            pass
        return lobby.game_size

    async def switch_owner(self, lobby_id: int, member_id: int) -> None:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)

        # Check if member is in lobby
        if any(member.member_id == member_id for member in lobby.member_lobbies):
            if not isinstance(lobby.history_thread_id, int):
                raise TypeError("History Thread ID not set.")

            # Send update embed
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_CHANGE,
                title=f"{(await self.get_member(lobby.guild_id, lobby.owner_id)).display_name}",
                destination=await self.get_thread(
                    lobby.guild_id, lobby.history_thread_id
                ),
                additional_string=f"<@{member_id}>",
            )

            # Update lobby owner
            lobby.owner_id = member_id
            await self.update_lobby(lobby)

    async def set_member_state(
        self, lobby_id: int, member_id: int, owner_set: bool = False
    ) -> bool:
        lobby, _ = await self._api_manager.toggle_member_ready(member_id, lobby_id)
        updated_state = next(
            member.ready
            for member in lobby.member_lobbies
            if member.member_id == member_id
        )

        if not isinstance(lobby.history_thread_id, int):
            raise TypeError("History Thread ID not set.")
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        member = await self.get_member(lobby.guild_id, member_id)
        if not owner_set and updated_state:
            member = await self.get_member(lobby.guild_id, member_id)
            pings = await self.get_unready_mentions(lobby)
            pings += await self.get_owner_mention(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.READY,
                title=member.display_name,
                destination=thread,
                pings=pings,
            )
        if owner_set:
            owner = await self.get_member(lobby.guild_id, lobby.owner_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_READY,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
                pings=await self.get_unready_mentions(lobby),
            )
        return updated_state

    async def set_description(self, lobby_id: int, description: str) -> None:
        """Set the description of the lobby"""
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        lobby.description = description
        await self._update_model_instance(lobby)

        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        if not isinstance(lobby.history_thread_id, int):
            raise TypeError("History Thread ID not set.")
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.DESCRIPTION_CHANGE,
            title=owner.display_name,
            destination=thread,
            additional_string=description,
        )

    async def set_has_joined_vc(self, member_id: int) -> None:
        lobbies = await self.get_all_lobbies()
        # TODO: Make it so a member can only be in one lobby.
        for lobby in lobbies:
            if member := next(
                (member
                for member in lobby.member_lobbies
                if member.member_id == member_id),
                None
            ):
                if member is None:
                    return
                elif member.has_joined_vc is False:
                    await self._api_manager.put_joined_vc(
                        member.lobby_id,
                        member.member_id,
                    )

    async def send_deletion_message(self, lobby_id: int, view: discord.ui.View) -> None:
        lobby = await self.get_lobby(lobby_id)

        thread_channel = await self.get_channel(lobby.guild_id, lobby.history_thread_id)
        if thread_channel is None:
            raise ThreadChannelNotFound
        
        owner_to_ping = await self.get_owner_mention(lobby.id)
        
        embed = discord.Embed(
            colour=discord.Colour.red(),
            title="Deletion Triggered",
            description="A member has left a full lobby from a voice channel. Will delete in 15 minutes!",
            timestamp=datetime.now()
        )

        message = await thread_channel.send(content=owner_to_ping, embed=embed, view=view)

        lobby.last_deletion_datetime = datetime.now(UTC)
        lobby.last_deletion_message_id = message.id
        lobby.state = LobbyStates.PENDING_DELETION

        await self.update_lobby(lobby)

    """Delete Functions"""

    async def remove_game(self, game_id: int) -> None:
        game, _ = await self._api_manager.get_game(game_id)
        # Clear cache before deleting as deletion raises an exception.
        self.transformer_cache.remove(str(game.guild_id), game_id)  # type: ignore
        await self._api_manager.delete_game(game_id)

    async def remove_member(
        self, lobby_id: int, member_id: int, owner_removed: bool = False
    ) -> None:
        lobby = await self.get_lobby(lobby_id)
        member = await self.get_member(lobby.guild_id, member_id)
        if not isinstance(lobby.history_thread_id, int):
            raise TypeError("History Thread ID not set.")
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)

        await self._api_manager.delete_member(member_id, lobby_id)
        if not owner_removed:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.LEAVE,
                title=member.display_name,
                destination=thread,
            )
        elif owner_removed:
            owner = await self.get_member(lobby.guild_id, lobby.owner_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_REMOVE,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
            )

    async def delete_lobby(
        self, lobby_id: int, reason: str | None = None, clean_up: bool = False
    ) -> None:
        try:
            lobby, _ = await self._api_manager.get_lobby(lobby_id)
        except LobbyNotFound:
            lobby = self.lobby_cache.get(str(lobby_id))
            if lobby is None:
                self.logger.error(
                    "Lobby was not found in cache, unable to delete lobby."
                )
                return

        original_channel = await self.get_channel(
            lobby.guild_id, lobby.original_channel_id
        )
        lobby_channel = await self.get_channel(lobby.guild_id, lobby.lobby_channel_id)
        owner = (
            "Bear Bot"
            if clean_up
            else (await self.get_member(lobby.guild_id, lobby.owner_id)).display_name
        )
        session_time = await self.get_session_time(lobby.created_datetime)

        try:
            await self._api_manager.delete_lobby(lobby_id)
        except DeletedLobby:
            self.lobby_cache.remove(str(lobby_id))

        embed_type = (
            self.embed_manager.UPDATE_TYPES.CLEAN_UP
            if clean_up
            else self.embed_manager.UPDATE_TYPES.DELETE
        )
        additional_string = lobby_id if clean_up else reason

        await self.embed_manager.send_update_embed(
            update_type=embed_type,
            title=owner,
            destination=original_channel,
            additional_string=str(additional_string) if additional_string else None,
            footer_string="⌚ " + session_time,
        )
        await lobby_channel.delete()

    """Helper Functions"""

    def print_lobby(self, lobby_id: int) -> None:
        print(self.get_lobby(lobby_id))

    async def has_joined(self, lobby_id: int, member_id: int) -> bool:
        lobby = await self.get_lobby(lobby_id)
        member_to_search = await self.get_member(lobby.guild_id, member_id)

        if len(lobby.member_lobbies) > 0:
            return member_to_search.id in [
                member.member_id for member in lobby.member_lobbies
            ]
        else:
            return False
        
    async def is_lobby_in_vc(self, lobby_id: int) -> bool:
        lobby = await self.get_lobby(lobby_id)
        has_all_joined_vc = all(member.has_joined_vc for member in lobby.member_lobbies)
        return has_all_joined_vc

    async def is_full(self, lobby_id: int) -> bool:
        """Check if the lobby is full"""
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        return False if len(lobby.member_lobbies) != lobby.game_size else True

    async def is_member_in_lobbies(self, member_id: int) -> tuple[bool, int | None]:
        """Checks if member is in any lobby"""
        lobbies = await self.get_all_lobbies()

        for lobby in lobbies:
            for member in lobby.member_lobbies:
                if member.member_id == member_id:
                    return True, lobby.id
            for queue_member in lobby.queue_member_lobbies:
                if queue_member.member_id == member_id:
                    return True, lobby.id
        
        return False, None

    async def can_promote(self, lobby: LobbyModel) -> bool:
        """Check if last promotion message is older than 10 minutes"""
        last_promotion_datetime = lobby.last_promotion_datetime
        if not last_promotion_datetime:
            return True

        localised_last_promotion_datetime = datetime.fromtimestamp(
            last_promotion_datetime.timestamp(), UTC,
        )

        last_promotion_duration = (
            datetime.now(UTC) - localised_last_promotion_datetime
        )

        if last_promotion_datetime is None or (last_promotion_duration) > timedelta(
            minutes=10
        ):
            return True
        else:
            return False

    async def get_lobbies_count(self) -> int:
        """Get the number of lobbies"""
        return len(await self._api_manager.get_lobbies())

    async def get_unready_mentions(self, lobby: LobbyModel) -> str:
        members_to_ping = await self.get_members_status(lobby.id, False)
        if len(members_to_ping) == 0:
            return ""
        mention_list = [f"<@{member.member_id}>" for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_all_mentions(self, lobby: LobbyModel) -> str:
        members_to_ping = await self.get_members(lobby)
        mention_list = [f"<@{member.id}>" for member in members_to_ping]
        return ", ".join(mention_list)

    @classmethod
    def member_id_to_mention(cls, member_id: int) -> str:
        return f"<@{member_id}>"
    
    @classmethod
    def role_id_to_mention(cls, role_id: int) -> str:
        return f"<@&{role_id}>"

    async def lobby_id_to_thread_mention(self, lobby_id: int) -> str:
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        assert lobby.history_thread_id is not None
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        return f"<#{thread.id}>"
    
    async def send_update_lock_embed(self, lobby_id: int):
        
        lobby = await self.get_lobby(lobby_id)
        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        if not isinstance(lobby.history_thread_id, int):
            raise TypeError("History Thread ID not set.")
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)

        if lobby.state is LobbyStates.ACTIVE:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.LOCK,
                title=owner.display_name,
                destination=thread,
                pings=await self.get_all_mentions(lobby),
            )
        else:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.UNLOCK,
                title=owner.display_name,
                destination=thread,
            )

    async def initialise_lobby_embed(self, lobby_id: int) -> None:
        from cog.lobby import ButtonView

        lobby_button_view = ButtonView(lobby_id=lobby_id, lobby_manager=self)
        lobby, _ = await self._api_manager.get_lobby(lobby_id)
        game, _ = await self._api_manager.get_game(lobby.game_id)
        assert lobby.lobby_channel_id is not None
        lobby_channel = await self.get_channel(lobby.guild_id, lobby.lobby_channel_id)
        description = lobby.description
        lobby_embed_message_id = await self.embed_manager.create_lobby_embed(
            lobby_id=lobby_id,
            owner=await self.get_member(lobby.guild_id, lobby.owner_id),
            description=description,
            is_full=False,
            members=await self.get_members(lobby),
            member_ready=[],
            game_name=game.name,
            game_size=lobby.game_size,
            channel=lobby_channel,
            view=lobby_button_view,
            state=LobbyStates.ACTIVE
        )
        assert lobby_embed_message_id is not None

        lobby.embed_message_id = lobby_embed_message_id

        queue_embed_message_id = await self.embed_manager.create_queue_embed(
            queue_members=[], channel=lobby_channel
        )

        assert queue_embed_message_id is not None
        lobby.queue_message_id = queue_embed_message_id

        await self._update_model_instance(lobby)
