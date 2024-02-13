from datetime import datetime, timedelta
from time import gmtime, strftime
from typing import Type, Union
from zoneinfo import ZoneInfo

import discord
from pydantic import BaseModel

from api.lobby_api import LobbyApi
from api.models import GameModel, InsertGameModel, InsertLobbyModel, LobbyModel, MemberLobbyModel, MemberModel
from cog.classes.utils import set_logger
from embeds.lobby_embed import LobbyEmbedManager
from exceptions.lobby_exceptions import MemberNotFound


class LobbyManager:
    def __init__(
        self,
        api_manager: LobbyApi,
        embed_manager: LobbyEmbedManager,
        bot: discord.Client,
    ) -> None:
        self._api_manager = api_manager
        self.bot = bot
        self.embed_manager = embed_manager
        self.logger = set_logger("lobby_manager")

    """Cache retrieval functions"""

    async def _get_guild(self, guild_id: int) -> discord.Guild:
        guild_from_cache = self.bot.get_guild(guild_id)
        if guild_from_cache:
            return guild_from_cache
        guild = await self.bot.fetch_guild(guild_id)
        if not guild:
            raise ValueError("Guild not found")
        return guild

    """Fetch functions"""

    async def get_lobby(self, lobby_id: int) -> LobbyModel:
        return await self._api_manager.get_lobby(lobby_id)

    async def get_all_lobbies(self) -> list[LobbyModel]:
        return await self._api_manager.get_lobbies()
    
    async def get_lobby_by_owner_id(self, owner_id: int) -> LobbyModel:
        return await self._api_manager.get_lobby_by_owner_id(owner_id)

    async def get_guild_id(self, lobby_id: int) -> int:
        lobby = await self._api_manager.get_lobby(lobby_id)
        return lobby.guild_id
    
    async def get_games_by_guild_id(self, guild_id: int) -> list[GameModel]:
        return await self._api_manager.get_games_by_guild_id(guild_id)
    
    async def get_game(self, game_id: int) -> GameModel:
        return await self._api_manager.get_game(game_id)

    async def get_thread(self, guild_id: int, thread_id: int) -> discord.Thread:
        guild = await self._get_guild(guild_id)

        history_thread_from_cache = guild.get_thread(thread_id)
        if history_thread_from_cache:
            return history_thread_from_cache

        history_thread = await guild.fetch_channel(thread_id)
        if not history_thread:
            raise ValueError("History thread not found")

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

    """Create functions"""

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
        return await self._api_manager.post_lobby(
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
    
    async def create_game(
        self,
        game_name: str,
        guild_id: int,
        max_size: int,
        role_id: int,
        icon_url: str | None
    ) -> GameModel:
        return await self._api_manager.post_game(
            InsertGameModel(
                name=game_name,
                guild_id=guild_id,
                max_size=max_size,
                role=role_id,
                icon_url=icon_url
            )
        )

    """Update functions"""

    async def _update_model_instance(
        self, instance: Union[LobbyModel, MemberModel, GameModel], model_cls: Type[BaseModel], lobby_id = None
    ) -> Union[LobbyModel, MemberModel, GameModel]:
        # Post the updated model instance to the appropriate function based on model type
        if model_cls is LobbyModel:
            return await self._api_manager.put_lobby(instance)
        elif model_cls is MemberModel:
            return await self._api_manager.put_member(lobby_id, instance)
        elif model_cls is GameModel:
            return await self._api_manager.put_game(instance)
        else:
            self.logger.warning(f"No specific handler found for {model_cls.__name__}.")
            raise NotImplementedError

    async def update_lobby(self, lobby: LobbyModel) -> LobbyModel:
        return await self._update_model_instance(lobby, LobbyModel)

    async def update_game_id(self, lobby_id: int, game_id: int) -> int:
        lobby = await self._api_manager.get_lobby(lobby_id)
        lobby.game_id = game_id
        await self._update_model_instance(lobby, LobbyModel)

        owner = await self.get_member(lobby.guild_id, lobby.owner_id)

        try:
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
        lobby = await self._api_manager.get_lobby(lobby_id)
        lobby.game_size = game_size
        await self._update_model_instance(lobby, LobbyModel)
        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        try:
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
        lobby = await self._api_manager.get_lobby(lobby_id)

        # Check if member is in lobby
        is_member = any(member.member_id == member_id for member in lobby.member_lobbies)
        
        if is_member:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_CHANGE,
                title=f"{(await self.get_member(lobby.guild_id, lobby.owner_id)).display_name}",
                destination=await self.get_thread(lobby.guild_id, lobby.history_thread_id),
                additional_string=f"<@{member_id}>"
            )
            lobby.owner_id = member_id
            await self.update_lobby(lobby)

    """Delete methods"""
    async def remove_game(self, game_id: int) -> None:
        await self._api_manager.delete_game(game_id)

    def print_lobby(self, lobby_id: int) -> None:
        print(self.get_lobby(lobby_id))

    async def get_members(self, lobby: LobbyModel) -> list[discord.Member]:
        list_of_members = [
            await self.get_member(lobby.guild_id, member.member_id) for member in lobby.member_lobbies
        ]
        final_list = list(filter(None, list_of_members))
        return final_list

    async def get_queue_members(self, lobby_id: int) -> list[discord.Member]:
        lobby = await self._api_manager.get_lobby(lobby_id)
        list_of_queue_members = [
            await self.get_member(lobby_id, member.member_id) for member in lobby.queue_member_lobbies
        ]
        final_list = list(filter(None, list_of_queue_members))
        return final_list

    async def add_member(
        self, lobby_id: int, member_id: int, owner_added: bool = False
    ) -> None:
        lobby = await self.get_lobby(lobby_id)
        member_model = await self._api_manager.post_member(lobby.id, MemberModel(id=member_id))
        member = await self.get_member(lobby.guild_id, member_model.id)
        thread = await self.get_thread(lobby.guild_id, lobby_id)
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

    async def remove_member(
        self, lobby_id: int, member_id: int, owner_removed: bool = False
    ) -> None:
        lobby = await self.get_lobby(lobby_id)
        member = await self.get_member(lobby.guild_id, member_id)
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

    async def set_member_state(
        self, lobby_id: int, member_id: int, owner_set: bool = False
    ) -> bool:
        updated_state = (await self._api_manager.toggle_member_ready(
            member_id, lobby_id
        )).ready

        lobby = await self.get_lobby(lobby_id)
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

    async def set_is_lobby_locked(self, lobby_id: int) -> bool:
        """Toggle the lock state of the lobby"""
        lobby = await self._api_manager.get_lobby(lobby_id)
        updated_is_locked = not lobby.is_locked
        lobby.is_locked = updated_is_locked

        await self._update_model_instance(lobby, LobbyModel)

        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)

        if updated_is_locked:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.LOCK,
                title=owner.display_name,
                destination=thread,
                pings=await self.get_all_mentions(lobby),
            )
        elif not updated_is_locked:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.UNLOCK,
                title=owner.display_name,
                destination=thread,
            )
        return lobby.is_locked

    async def has_joined(self, lobby_id: int, member_id: int) -> bool:
        lobby = await self.get_lobby(lobby_id)
        member_to_search = await self.get_member(lobby.guild_id, member_id)

        if len(lobby.member_lobbies) > 0:
            return member_to_search.id in [member.member_id for member in lobby.member_lobbies]
        else:
            return False

    async def get_members_status(self, lobby_id: int, ready_status: bool) -> list[MemberLobbyModel]:
        """Get the number of members that are ready"""
        lobby = await self._api_manager.get_lobby(lobby_id)
        return [member for member in lobby.member_lobbies if member.ready == ready_status]

    async def delete_lobby(
        self, lobby_id: int, reason: str | None = None, clean_up: bool = False
    ) -> None:
        """Delete a lobby"""
        lobby = await self._api_manager.get_lobby(lobby_id)
        original_channel = await self.get_channel(lobby.guild_id, lobby.original_channel_id)
        session_time = await self.get_session_time(lobby.created_datetime)
        owner = (
            "Bear Bot"
            if clean_up
            else (await self.get_member(lobby.guild_id, lobby.owner_id)).display_name
        )

        await self._api_manager.delete_lobby(lobby_id)

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

    async def set_description(self, lobby_id: int, description: str) -> None:
        """Set the description of the lobby"""
        lobby = await self._api_manager.get_lobby(lobby_id)
        lobby.description = description
        await self._update_model_instance(lobby, LobbyModel)

        owner = await self.get_member(lobby.guild_id, lobby.owner_id)
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.DESCRIPTION_CHANGE,
            title=owner.display_name,
            destination=thread,
            additional_string=description,
        )

    async def is_full(self, lobby_id: int) -> bool:
        """Check if the lobby is full"""
        lobby = await self._api_manager.get_lobby(lobby_id)
        return False if len(lobby.member_lobbies) != lobby.game_size else True

    async def get_session_time(self, created_datetime: datetime) -> str:
        """Get the session time of the lobby"""
        timezone = ZoneInfo("Pacific/Auckland")

        localised_creation_datetime = created_datetime.astimezone(tz=timezone)
        localised_datetime_now = datetime.utcnow().astimezone(tz=timezone)

        duration = localised_datetime_now - localised_creation_datetime
        return "Session Duration: " + strftime(
            "%H:%M:%S", gmtime(duration.total_seconds())
        )

    async def can_promote(self, lobby: LobbyModel) -> bool:
        """Check if last promotion message is older than 10 minutes"""
        last_promotion_datetime = lobby.last_promotion_datetime
        if not last_promotion_datetime:
            return True

        if last_promotion_datetime is None or (
            datetime.utcnow() - last_promotion_datetime.utcnow()
        ) > timedelta(minutes=10):
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

    async def get_ready_mentions(self, lobby_id: int) -> str:
        members_to_ping = await self.get_members_status(lobby_id, True)
        mention_list = [f"<@{member}>" for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_all_mentions(self, lobby: LobbyModel) -> str:
        members_to_ping = await self.get_members(lobby)
        mention_list = [f"<@{member.id}>" for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_owner_mention(self, lobby_id: int) -> str:
        lobby = await self._api_manager.get_lobby(lobby_id)
        return f"<@{(await self.get_member(lobby.guild_id, lobby.owner_id)).id}>"

    def member_id_to_mention(self, member_id: int) -> str:
        return f"<@{member_id}>"

    async def lobby_id_to_thread_mention(self, lobby_id: int) -> str:
        lobby = await self._api_manager.get_lobby(lobby_id)
        thread = await self.get_thread(lobby.guild_id, lobby.history_thread_id)
        return f"<#{thread.id}>"

    async def initialise_lobby_embed(
        self, lobby_id: int
    ) -> None:
        from cog.lobby import ButtonView

        lobby_button_view = ButtonView(
            lobby_id=lobby_id,
            lobby_manager=self
        )
        lobby = await self._api_manager.get_lobby(lobby_id)
        lobby_channel = await self.get_channel(lobby.guild_id, lobby.lobby_channel_id)
        description = lobby.description
        lobby_embed_message_id = await self.embed_manager.create_lobby_embed(
            lobby_id=lobby_id,
            owner=await self.get_member(lobby.guild_id, lobby.owner_id),
            description=description,
            is_locked=False,
            is_full=False,
            members=await self.get_members(lobby),
            member_ready=[],
            game_size=lobby.game_size,
            channel=lobby_channel,
            view=lobby_button_view,
        )
        assert lobby_embed_message_id is not None

        lobby.embed_message_id = lobby_embed_message_id

        queue_embed_message_id = await self.embed_manager.create_queue_embed(
            queue_members=[], channel=lobby_channel
        )

        assert queue_embed_message_id is not None
        lobby.queue_message_id = queue_embed_message_id
        
        await self._update_model_instance(lobby, LobbyModel)
