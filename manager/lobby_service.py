from collections.abc import Sequence
import discord
from embeds.lobby_embed import LobbyEmbedManager
from repository.lobby_repo import LobbyPostgresRepository, MemberNotFound
from repository.tables import GuildModel, LobbyModel, MemberModel


class LobbyManager:

    def __init__(
        self,
        # TODO: Make this an ABC to allow for other repositories
        repository: LobbyPostgresRepository,
        embed_manager: LobbyEmbedManager,
        bot: discord.Client
    ) -> None:
        self._repository = repository
        self.bot = bot
        self.embed_manager = embed_manager

    def _get_repository(self) -> LobbyPostgresRepository:
        if self._repository:
            return self._repository
        else:
            raise AttributeError('Repository has not been set')

    async def _get_guild(self, lobby_id: int) -> discord.Guild:
        guild_id = await self._get_repository().get_guild_id(lobby_id)
        guild_from_cache = self.bot.get_guild(guild_id)
        if guild_from_cache:
            return guild_from_cache
        guild = await self.bot.fetch_guild(guild_id)
        if not guild:
            raise ValueError('Guild not found')
        return guild

    async def get_guild(self, guild_id: int) -> GuildModel:
        return await self._repository.get_guild(guild_id)

    async def get_lobby(self, lobby_id: int) -> LobbyModel:
        return await self._get_repository().get_lobby(lobby_id)

    async def get_all_lobbies(self) -> Sequence[LobbyModel]:
        return await self._get_repository().get_all_lobbies()

    async def create_lobby(
        self,
        control_panel_message_id: int,
        original_channel_id: int,
        lobby_channel_id: int,
        guild_id: int,
        guild_name: str,
        user_id: int,
        game_id: int | None = None,
        max_size: int | None = None,
        description: str | None = None,
    ) -> int:
        return await self._get_repository().create_lobby(
            control_panel_message_id,
            original_channel_id,
            lobby_channel_id,
            guild_id,
            guild_name,
            user_id,
            game_id,
            max_size,
            description,
        )

    async def get_guild_id(self, lobby_id: int) -> int:
        return await self._get_repository().get_guild_id(lobby_id)

    async def get_thread(self, lobby_id: int) -> discord.Thread:
        history_thread_id = await self._get_repository().get_thread_id(lobby_id)
        assert history_thread_id
        guild = await self._get_guild(lobby_id)

        history_thread_from_cache = guild.get_thread(history_thread_id)
        if history_thread_from_cache:
            return history_thread_from_cache

        history_thread = await guild.fetch_channel(history_thread_id)
        if not history_thread:
            raise ValueError('History thread not found')
        return history_thread  # type: ignore

    async def set_thread(self, lobby_id: int, thread_id: int) -> None:
        await self._get_repository().set_thread_id(lobby_id, thread_id)

    async def get_game_id(self, lobby_id: int) -> int:
        return await self._get_repository().get_game_id(lobby_id)

    async def set_game_id(self, lobby_id: int, game_id: int) -> int:
        owner = await self.get_lobby_owner(lobby_id)
        game_id = await self._get_repository().set_game_id(lobby_id, game_id)
        try:
            thread = await self.get_thread(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.GAME_CHANGE,
                title=owner.display_name,
                destination=thread,
                additional_string=str(game_id),
            )
        except Exception:
            pass
        return game_id

    async def get_gamesize(self, lobby_id: int) -> int:
        return await self._get_repository().get_gamesize(lobby_id)

    async def set_gamesize(self, lobby_id: int, game_size: int) -> int:
        game_size = await self._get_repository().set_gamesize(lobby_id, game_size)
        owner = await self.get_lobby_owner(lobby_id)
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.GAME_CHANGE,
            title=owner.display_name,
            destination=await self.get_thread(lobby_id),
            additional_string=str(game_size),
        )
        return game_size

    async def get_lobby_name(self) -> str:
        lobby_number = len(await self._get_repository().get_all_lobbies()) + 1
        return f'Lobby {lobby_number}'

    async def get_lobby_channel(self, lobby_id: int) -> discord.TextChannel:
        lobby_channel_id = await self._get_repository().get_lobby_channel_id(lobby_id)
        guild = await self._get_guild(lobby_id)

        lobby_channel_from_cache = guild.get_channel(lobby_channel_id)
        if lobby_channel_from_cache:
            assert isinstance(lobby_channel_from_cache, discord.TextChannel)
            return lobby_channel_from_cache

        lobby_channel_from_fetch = await guild.fetch_channel(lobby_channel_id)
        if not lobby_channel_from_fetch:
            raise ValueError('Lobby channel not found')
        return lobby_channel_from_fetch  # type: ignore

    async def get_lobby_owner(self, lobby_id: int) -> discord.Member:
        member_model = await self._get_repository().get_owner(lobby_id)
        member = await self.get_member(lobby_id, member_model.id)
        return member

    def print_lobby(self, lobby_id: int) -> None:
        print(self.get_lobby(lobby_id))

    async def get_original_channel(self, lobby_id: int) -> discord.TextChannel:
        original_channel_id = await self._get_repository().get_original_channel_id(
            lobby_id
        )
        guild = await self._get_guild(lobby_id)
        original_channel_from_cache = guild.get_channel(original_channel_id)
        if original_channel_from_cache:
            assert isinstance(original_channel_from_cache, discord.TextChannel)
            return original_channel_from_cache

        original_channel_from_fetch = await guild.fetch_channel(original_channel_id)
        if not original_channel_from_fetch:
            raise ValueError('Original channel not found')
        return original_channel_from_fetch  # type: ignore

    async def get_control_panel_message(
        self,
        lobby_id: int
    ) -> discord.Message | discord.PartialMessage:
        control_panel_id = await self._get_repository().get_control_panel_message_id(
            lobby_id
        )
        lobby_text_channel = await self.get_lobby_channel(lobby_id)
        assert lobby_text_channel

        control_panel_message_from_cache = lobby_text_channel.get_partial_message(
            control_panel_id
        )
        if control_panel_message_from_cache:
            return control_panel_message_from_cache

        control_panel_message_from_fetch = await lobby_text_channel.fetch_message(
            control_panel_id
        )
        if not control_panel_message_from_fetch:
            raise ValueError('Control panel message not found')
        return control_panel_message_from_fetch

    async def get_embed_message(
        self,
        lobby_id: int
    ) -> None | discord.Message | discord.PartialMessage:
        embed_message_id = await self._get_repository().get_embed_message_id(lobby_id)
        lobby_text_channel = await self.get_lobby_channel(lobby_id)
        assert lobby_text_channel
        if not embed_message_id:
            return None
        embed_message_from_cache = lobby_text_channel.get_partial_message(
            embed_message_id
        )
        if embed_message_from_cache:
            return embed_message_from_cache

        embed_message_from_fetch = await lobby_text_channel.fetch_message(
            embed_message_id
        )
        return embed_message_from_fetch

    async def set_embed_message(self, lobby_id: int, embed_message_id: int) -> None:
        await self._get_repository().set_embed_message_id(lobby_id, embed_message_id)

    async def get_queue_embed_message(
        self,
        lobby_id: int
    ) -> None | discord.Message | discord.PartialMessage:
        queue_embed_message_id = await self._get_repository().get_queue_message_id(
            lobby_id
        )
        lobby_text_channel = await self.get_lobby_channel(lobby_id)
        assert lobby_text_channel
        if not queue_embed_message_id:
            return None
        queue_embed_message_from_cache = lobby_text_channel.get_partial_message(
            queue_embed_message_id
        )
        if queue_embed_message_from_cache:
            return queue_embed_message_from_cache
        queue_embed_message_from_fetch = await lobby_text_channel.fetch_message(
            queue_embed_message_id
        )
        return queue_embed_message_from_fetch

    async def set_queue_message(self, lobby_id: int, queue_message_id: int) -> None:
        await self._get_repository().set_queue_message_id(lobby_id, queue_message_id)

    async def get_member_model(self, member_id: int) -> MemberModel:
        member = await self._get_repository().get_member(member_id)
        if not member:
            raise MemberNotFound(member_id)
        return member

    async def get_member(self, lobby_id: int, member_id: int) -> discord.Member:
        guild = await self._get_guild(lobby_id)

        member_from_cache = guild.get_member(member_id)
        if member_from_cache:
            return member_from_cache

        member_from_fetch = await guild.fetch_member(member_id)
        if member_from_fetch:
            return member_from_fetch

        raise MemberNotFound(member_id)

    async def get_members(self, lobby_id: int) -> list[discord.Member]:
        member_list: Sequence[MemberModel] = await self._get_repository().get_members(
            lobby_id
        )
        list_of_members = [await self.get_member(lobby_id, member.id)
                           for member in member_list]
        final_list = list(filter(None, list_of_members))
        return final_list

    async def get_queue_members(self, lobby_id: int) -> list[discord.Member]:
        queue_member_list = await self._get_repository().get_queue_members(lobby_id)
        list_of_queue_members = [await self.get_member(lobby_id, member.id)
                                 for member in queue_member_list]
        final_list = list(filter(None, list_of_queue_members))
        return final_list

    async def add_member(
        self,
        lobby_id: int,
        member_id: int,
        owner_added: bool = False
    ) -> None:
        await self._get_repository().add_member(lobby_id, member_id)
        member = await self.get_member(lobby_id, member_id)
        thread = await self.get_thread(lobby_id)
        if not owner_added:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.JOIN,
                title=member.display_name,
                destination=thread,
            )
        elif owner_added:
            owner = await self.get_lobby_owner(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_ADD,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
            )

    async def add_member_queue(self, lobby_id: int, member_id: int) -> None:
        await self._get_repository().add_queue_member(lobby_id, member_id)

    async def remove_member(
        self,
        lobby_id: int,
        member_id: int,
        owner_removed: bool = False
    ) -> None:
        member = await self.get_member(lobby_id, member_id)
        thread = await self.get_thread(lobby_id)
        await self._get_repository().remove_member(lobby_id, member_id)
        if not owner_removed:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.LEAVE,
                title=member.display_name,
                destination=thread,
            )
        elif owner_removed:
            owner = await self.get_lobby_owner(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_REMOVE,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
            )

    async def move_queue_members(self, lobby_id: int) -> None:
        await self._get_repository().move_queue_members(lobby_id)

    async def set_member_state(
        self,
        lobby_id: int,
        member_id: int,
        owner_set: bool = False
    ) -> bool:
        updated_state = await self._get_repository().set_member_state(
            lobby_id,
            member_id
        )
        thread = await self.get_thread(lobby_id)
        member = await self.get_member(lobby_id, member_id)
        if not owner_set and updated_state:
            member = await self.get_member(lobby_id, member_id)
            pings = await self.get_unready_mentions(lobby_id)
            pings += await self.get_owner_mention(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.READY,
                title=member.display_name,
                destination=thread,
                pings=pings,
            )
        if owner_set:
            owner = await self.get_lobby_owner(lobby_id)
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.OWNER_READY,
                title=owner.display_name,
                additional_string=member.display_name,
                destination=thread,
                pings=await self.get_unready_mentions(lobby_id),
            )
        return updated_state

    async def get_member_state(self, lobby_id: int, member_id: int) -> bool:
        return await self._get_repository().get_member_state(lobby_id, member_id)

    async def get_is_lobby_lock(self, lobby_id: int) -> bool:
        '''Get the lock state of the lobby'''
        return await self._get_repository().is_lobby_locked(lobby_id)

    async def set_is_lobby_locked(self, lobby_id: int) -> bool:
        '''Toggle the lock state of the lobby'''
        is_locked = await self._get_repository().is_lobby_locked(lobby_id)
        updated_is_locked = await self._get_repository().set_is_lobby_locked(
            lobby_id,
            not is_locked
        )
        owner = await self.get_lobby_owner(lobby_id)
        thread = await self.get_thread(lobby_id)

        if updated_is_locked:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.LOCK,
                title=owner.display_name,
                destination=thread,
                pings=await self.get_all_mentions(lobby_id)
            )
        elif not updated_is_locked:
            await self.embed_manager.send_update_embed(
                update_type=self.embed_manager.UPDATE_TYPES.UNLOCK,
                title=owner.display_name,
                destination=thread,
            )
        return not is_locked

    async def has_joined(self, lobby_id: int, member_id: int) -> bool:
        return await self._get_repository().has_joined(lobby_id, member_id)

    async def switch_owner(self, lobby_id: int, member_id: int) -> None:
        '''Swap a member with the owner of the lobby'''
        old_owner = await self.get_lobby_owner(lobby_id)
        await self._get_repository().set_owner(lobby_id, member_id)
        new_owner = await self.get_member(lobby_id, member_id)
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.OWNER_CHANGE,
            title=old_owner.display_name,
            destination=await self.get_thread(lobby_id),
            additional_string=new_owner.display_name,
            pings=self.member_id_to_mention(new_owner.id)
        )

    async def search_new_owner(self, lobby_id: int) -> int | None:
        '''Choose the next owner in lobby and move next owner up to first slot'''
        return await self._get_repository().search_new_owner(lobby_id)

    async def get_member_length(self, lobby_id: int) -> int:
        '''Get the number of members in the lobby'''
        return len(await self._get_repository().get_members(lobby_id))

    async def get_members_ready(self, lobby_id: int) -> Sequence[int]:
        '''Get the number of members that are ready'''
        return await self._get_repository().get_members_ready(lobby_id)

    async def get_members_not_ready(self, lobby_id: int) -> Sequence[int]:
        '''Get the list of members that are not ready'''
        return await self._get_repository().get_members_not_ready(lobby_id)

    async def delete_lobby(self, lobby_id: int, reason: str | None = None) -> None:
        '''Delete a lobby'''
        owner = await self.get_lobby_owner(lobby_id)
        original_channel = await self.get_original_channel(lobby_id)
        session_time = await self.get_session_time(lobby_id)
        await self._get_repository().delete_lobby(lobby_id)
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.DELETE,
            title=owner.display_name,
            destination=original_channel,
            additional_string=reason,
            footer_string="⌚ " + session_time,
        )

    async def get_description(self, lobby_id: int) -> str | None:
        '''Get the description of the lobby'''
        return await self._get_repository().get_description(lobby_id)

    async def set_description(self, lobby_id: int, description: str) -> None:
        '''Set the description of the lobby'''
        description = await self._get_repository().set_description(
            lobby_id,
            description
        )
        await self.embed_manager.send_update_embed(
            update_type=self.embed_manager.UPDATE_TYPES.DESCRIPTION_CHANGE,
            title=description,
            destination=await self.get_thread(lobby_id),
            additional_string=description,
        )

    async def is_full(self, lobby_id: int) -> bool:
        '''Check if the lobby is full'''
        return await self._get_repository().is_full(lobby_id)

    async def get_session_time(self, lobby_id: int) -> str:
        '''Get the session time of the lobby'''
        return await self._get_repository().get_session_time(lobby_id)

    async def get_last_promotion_message(
        self,
        lobby_id: int
    ) -> discord.Message | discord.PartialMessage | None:
        '''Get the last promotion message'''
        last_promotion_message_id = await self._get_repository().\
            get_last_promotion_message_id(lobby_id)
        if not last_promotion_message_id:
            return None

        original_lobby_text_channel = await self.get_original_channel(lobby_id)
        if not original_lobby_text_channel:
            return None
        channel_from_cache = original_lobby_text_channel.get_partial_message(
            last_promotion_message_id
        )
        if channel_from_cache:
            return channel_from_cache
        channel_from_fetch = await original_lobby_text_channel.fetch_message(
            last_promotion_message_id
        )
        if channel_from_fetch:
            return channel_from_fetch
        else:
            return None

    async def can_promote(self, lobby_id: int) -> bool:
        '''Check if last promotion message is older than 10 minutes'''
        return await self._get_repository().can_promote(lobby_id)

    async def set_last_promotion_message(self, lobby_id: int, message_id: int) -> None:
        '''Set the last promotion message'''
        await self._get_repository().set_last_promotion_message_id(lobby_id, message_id)

    async def is_owner_of_lobby(self, member_id: int) -> bool:
        '''Check if a member is the owner of a lobby'''
        return await self._get_repository().is_owner_of_lobby(member_id)

    async def get_lobbies_count(self) -> int:
        '''Get the number of lobbies'''
        return await self._get_repository().get_lobbies_count()

    async def get_lobby_by_owner_id(self, owner_id: int) -> LobbyModel:
        '''Get the id of a lobby by owner id'''
        return await self._get_repository().get_lobby_by_owner_id(owner_id)

    async def get_lobby_id_by_owner_id(self, owner_id: int) -> int:
        '''Get the id of a lobby by owner'''
        return await self._get_repository().get_lobby_id_by_owner_id(owner_id)

    async def get_unready_mentions(self, lobby_id: int) -> str:
        members_to_ping = await self.get_members_not_ready(lobby_id)
        if len(members_to_ping) == 0:
            return ""
        mention_list = [f'<@{member}>' for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_ready_mentions(self, lobby_id: int) -> str:
        members_to_ping = await self.get_members_ready(lobby_id)
        mention_list = [f'<@{member}>' for member in members_to_ping]
        return ", ".join(mention_list)
    
    async def get_all_mentions(self, lobby_id: int) -> str:
        members_to_ping = await self.get_members(lobby_id)
        mention_list = [f'<@{member.id}>' for member in members_to_ping]
        return ", ".join(mention_list)

    async def get_owner_mention(self, lobby_id: int) -> str:
        return f'<@{(await self.get_lobby_owner(lobby_id)).id}>'

    def member_id_to_mention(self, member_id: int) -> str:
        return f'<@{member_id}>'

    async def lobby_id_to_thread_mention(self, lobby_id: int) -> str:
        thread = await self.get_thread(lobby_id)
        return f'<#{thread.id}>'

    from manager.game_service import GameManager

    async def initialise_lobby_embed(
        self,
        lobby_id: int,
        game_manager: GameManager
    ) -> None:
        from cog.lobby import ButtonView
        lobby_button_view = ButtonView(
            lobby_id=lobby_id,
            lobby_manager=self,
            game_manager=game_manager,
        )
        lobby_channel = await self.get_lobby_channel(lobby_id)
        description = await self.get_description(lobby_id)
        lobby_embed_message_id = await self.embed_manager.create_lobby_embed(
            lobby_id=lobby_id,
            owner=await self.get_lobby_owner(lobby_id),
            description=description,
            is_locked=False,
            is_full=False,
            members=await self.get_members(lobby_id),
            member_ready=[],
            game_size=await self.get_gamesize(lobby_id),
            channel=lobby_channel,
            view=lobby_button_view
        )
        assert lobby_embed_message_id is not None
        await self.set_embed_message(lobby_id, lobby_embed_message_id)

        queue_embed_message_id = await self.embed_manager.create_queue_embed(
            queue_members=[],
            channel=lobby_channel
        )
        assert queue_embed_message_id is not None
        await self.set_queue_message(lobby_id, queue_embed_message_id)
