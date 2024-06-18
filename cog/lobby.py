import asyncio
from datetime import datetime, time, timedelta
from datetime import UTC as UTC
from zoneinfo import ZoneInfo

from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    Embed,
    Interaction,
    Member,
    NotFound,
    PermissionOverwrite,
    Role,
    SelectOption,
    TextChannel,
    TextStyle,
    VoiceState,
    app_commands,
    threads,
    utils,
)
from discord.ext import commands, tasks
from discord.ui import Button, Modal, Select, TextInput, View, button

from api.api_exceptions import GamesNotFound
from api.lobby_api import LobbyApi
from api.models import LobbyModel, LobbyStates
from api.session_manager import ClientSessionManager
from cog.classes.lobby.lobby_cache import LobbyCache
from cog.classes.lobby.transformer_error import GameTransformError, NumberTransformError
from cog.classes.lobby.transformer_cache import TransformerCache
from cog.classes.utils import set_logger
from embeds.lobby_embed import LobbyEmbedManager
from exceptions.lobby_exceptions import (
    DeletedGame,
    DeletedLobby,
    LobbyChannelNotFound,
    LobbyNotFound,
    MemberAlreadyInLobby,
    MemberNotFound,
    MessageNotFound,
    ServerConnectionException,
    ThreadChannelNotFound,
)
from manager.lobby_service import LobbyManager

transformer_cache = TransformerCache()
lobby_cache = LobbyCache()
scheduled_clean_up_time = time(5, 0, 0, 0, tzinfo=ZoneInfo("Pacific/Auckland"))


# Predicate for commands
def is_lobby_thread():
    """Checks if the interaction is in a lobby thread"""

    def predicate(interaction: Interaction) -> bool:
        assert interaction.channel is not None
        return isinstance(interaction.channel, threads.Thread)

    return app_commands.check(predicate)


class GameTransformer(app_commands.Transformer):

    async def transform(self, interaction: Interaction, argument: str) -> int:
        assert interaction.guild is not None
        games = transformer_cache.get(str(interaction.guild.id))
        if games is None:
            raise GameTransformError("There are no games for this server.")
        try:
            value = int(argument)
            for game in games:
                if value == game.id:
                    return game.id
            else:
                raise GameTransformError(f"Game_id: {argument} not found")
        except ValueError:
            raise GameTransformError(f"Game_id: {argument} not found")

    async def autocomplete(
        self, interaction: Interaction, value: int | float | str, /
    ) -> list[app_commands.Choice[int | float | str]]:
        assert interaction.guild is not None
        list_of_options: list[app_commands.Choice[int | float | str]] = []

        games = transformer_cache.get(str(interaction.guild.id))
        # If there are no games available, return an empty list
        if not games or len(games) == 0:
            return list_of_options
        # If nothing is inputted, return all games
        if value == "":
            for game in games:
                list_of_options.append(
                    app_commands.Choice(name=game.name, value=str(game.id))
                )
        else:
            # If there is an input, return all games that start with the input
            for game in games:
                if game.name.lower().startswith(str(value).lower()):
                    list_of_options.append(
                        app_commands.Choice(name=game.name, value=str(game.id))
                    )
        return list_of_options


class NumberTransformer(app_commands.Transformer):

    async def transform(self, interaction: Interaction, argument: str) -> int:
        assert interaction.guild is not None
        try:
            game_id: str = interaction.namespace["game"]
            games = transformer_cache.get(str(interaction.guild.id))
            if games is None:
                raise NumberTransformError("There are no games in this server")
            # Find the GameModel with the matching game_id
            try:
                game_model = next(
                    (game for game in games if game.id == int(game_id)), None
                )
            except Exception:
                raise
            if game_model is None:
                raise ValueError
            max_size = game_model.max_size
            number = int(argument)
            if number < 2:
                return 2
            if number > max_size:
                return max_size
            return number
        except ValueError:
            raise NumberTransformError

    async def autocomplete(
        self, interaction: Interaction, value: int | float | str, /
    ) -> list[app_commands.Choice[int | float | str]]:
        list_of_options: list[app_commands.Choice[int | float | str]] = []
        assert interaction.guild is not None
        game_id = interaction.namespace["game"]
        if game_id is None:
            return list_of_options
        try:
            games = transformer_cache.get(str(interaction.guild.id))

            if games is None:
                raise NumberTransformError("No games on this server")

            # Find the GameModel with the matching game_id
            game_model = next((game for game in games if game.id == int(game_id)), None)
            if game_model is not None:
                max_size = game_model.max_size
                if value is None:
                    for i in range(1, max_size):
                        list_of_options.append(
                            app_commands.Choice(name=str(i + 1), value=str(i + 1))
                        )
                else:
                    for i in range(1, max_size):
                        if str(i + 1).startswith(str(value)):
                            list_of_options.append(
                                app_commands.Choice(name=str(i + 1), value=str(i + 1))
                            )
            return list_of_options
        except ValueError as e:
            print(e)
            return list_of_options


class DescriptionModal(Modal, title="Edit Description"):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__()
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    answer = TextInput(  # type: ignore
        label="Edit Description", style=TextStyle.paragraph, max_length=50
    )

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        await self.lobby_manager.set_description(self.lobby_id, self.answer.value)
        interaction.client.dispatch("update_lobby_embed", self.lobby_id)  # type: ignore


class DeletionConfirmationModal(Modal, title="Are you sure? Reason optional."):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__()
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    reason = TextInput(label="Reason", max_length=150, required=False)  # type: ignore

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer()
        lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        lobby_channel = await self.lobby_manager.get_channel(
            lobby.guild_id,
            lobby.lobby_channel_id,
        )
        await self.lobby_manager.delete_lobby(
            lobby_id=self.lobby_id,
            reason=self.reason.value,
        )


class OwnerSelectView(View):
    def __init__(
        self,
        lobby_id: int,
        lobby_manager: LobbyManager,
        list_of_users: list[tuple[str, int]],
    ):
        super().__init__()
        self.list_of_users = list_of_users
        self.add_item(self.OwnerDropdown(lobby_id, list_of_users, lobby_manager))

    class OwnerDropdown(Select):
        def __init__(
            self,
            lobby_id: int,
            list_of_users: list[tuple[str, int]],
            lobby_manager: LobbyManager,
        ):
            options = []

            for user in list_of_users:
                options.append(SelectOption(label=user[0], value=str(user[1])))

            super().__init__(
                placeholder="Choose new owner...",
                min_values=1,
                max_values=1,
                options=options,
            )
            self.lobby_id = lobby_id
            self.lobby_manager = lobby_manager

        async def callback(self, interaction: Interaction):
            await interaction.response.defer()
            lobby = await self.lobby_manager.get_lobby(self.lobby_id)
            lobby_owner = await self.lobby_manager.get_member(
                lobby.guild_id, lobby.owner_id
            )
            if interaction.user != lobby_owner:
                return

            assert interaction.guild is not None
            member = interaction.guild.get_member(int(self.values[0]))
            assert member is not None
            await self.lobby_manager.switch_owner(self.lobby_id, member.id)
            interaction.client.dispatch(  # type: ignore
                "update_lobby_embed", self.lobby_id
            )

            # Disable view after selection
            if self.view is not None:
                self.disabled = True
                await interaction.edit_original_response(view=self.view)
                self.view.stop()


class DeletionButtonView(View):
    def __init__(
        self,
        lobby_id: int,
        lobby_manager: LobbyManager,
        bot: commands.Bot,
        *,
        timeout: float | None = 900,
    ):
        """Deletion prompt that will timeout in 15mins to delete."""
        super().__init__(timeout=timeout)
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager
        self.bot = bot

    @button(label="Delete", style=ButtonStyle.red, custom_id="delete_button")
    async def delete_button(self, interaction: Interaction, _: Button):
        await interaction.response.defer()
        lobby = lobby_cache.get(str(self.lobby_id))
        if lobby is None:
            lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        if interaction.user.id == lobby.owner_id:
            await self.lobby_manager.delete_lobby(lobby_id=self.lobby_id)

    @button(label="Cancel", style=ButtonStyle.blurple, custom_id="cancel_button")
    async def cancel_button(self, interaction: Interaction, _: Button):
        await interaction.response.defer()
        lobby = lobby_cache.get(str(self.lobby_id))
        if lobby is None:
            lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        if interaction.user.id == lobby.owner_id:
            message = await self.lobby_manager.get_message(
                lobby.guild_id, lobby.history_thread_id, lobby.last_deletion_message_id
            )
            if not message:
                raise MessageNotFound
            lobby.state = LobbyStates.ACTIVE
            lobby.last_deletion_datetime = None
            lobby.last_deletion_message_id = None
            await self.lobby_manager.update_lobby(lobby)
            await message.delete()

    async def on_timeout(self) -> None:
        await self.lobby_manager.delete_lobby(
            lobby_id=self.lobby_id,
            reason=f"🧼 {self.bot.user.display_name} has cleaned up this lobby!",
        )


class ButtonView(View):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__(timeout=None)
        self.id = str(lobby_id)
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    async def on_error(self, interaction: Interaction, error, item):
        member_to_mention = self.lobby_manager.member_id_to_mention(interaction.user.id)
        if isinstance(error, MemberAlreadyInLobby):
            embed = Embed(
                title="🚫 Sorry, cannot join...",
                description=error.message,
                color=Color.red(),
            )
            await error.thread.send(content=member_to_mention, embed=embed)

    @button(label="Join", style=ButtonStyle.green, custom_id="join_button")
    async def join_button(self, interaction: Interaction, button: Button):

        # Check if the member has already joined
        await interaction.response.defer()
        if await self.lobby_manager.has_joined(self.lobby_id, interaction.user.id):
            return

        # Find if the member is in any lobby or queue
        is_member_in_lobby, lobby_id = await self.lobby_manager.is_member_in_lobbies(
            interaction.user.id
        )

        if is_member_in_lobby:
            raise MemberAlreadyInLobby(
                display_name=interaction.user.display_name,
                lobby_id=lobby_id,
                thread=await self.lobby_manager.get_thread(
                    interaction.guild_id,
                    lobby_cache.get(str(self.lobby_id)).history_thread_id,
                ),
            )

        await self.lobby_manager.add_member(self.lobby_id, interaction.user.id)

        # Check if user is already in voice channel.
        if interaction.user.voice and interaction.user.voice.channel:
            await self.lobby_manager.set_has_joined_vc(interaction.user.id)

        interaction.client.dispatch("update_lobby_embed", self.lobby_id)  # type: ignore

    @button(label="Ready", style=ButtonStyle.green, custom_id="ready_button")
    async def ready(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        # Reject interaction if user is not in lobby
        has_joined = await self.lobby_manager.has_joined(
            self.lobby_id, interaction.user.id
        )
        if not has_joined:
            # Defer interaction update
            return

        # Reject interaction if lobby is locked
        is_locked = (
            await self.lobby_manager.get_lobby(self.lobby_id)
        ).state is LobbyStates.LOCKED
        if is_locked:
            # Defer interaction update
            return

        # Update member state
        await self.lobby_manager.set_member_state(self.lobby_id, interaction.user.id)

        # Update button
        number_filled = len(
            await self.lobby_manager.get_members_status(self.lobby_id, True)
        )
        button.label = f"Ready: {number_filled}"
        await interaction.edit_original_response(view=self)

        # Update lobby embed
        interaction.client.dispatch("update_lobby_embed", self.lobby_id)  # type: ignore

    @button(label="Leave", style=ButtonStyle.red, custom_id="leave_button")
    async def leave(self, interaction: Interaction, _: Button):
        await interaction.response.defer()
        # Check if user is in lobby
        if not await self.lobby_manager.has_joined(self.lobby_id, interaction.user.id):
            return

        # Check if user is in queue
        queue_list = await self.lobby_manager.get_queue_members(self.lobby_id)
        filtered_list = list(
            filter(lambda member: member.id == interaction.user.id, queue_list)
        )
        if len(filtered_list) > 0:
            await self.lobby_manager.remove_member(self.lobby_id, interaction.user.id)
            interaction.client.dispatch(  # type: ignore
                "update_lobby_embed", self.lobby_id
            )
            return

        try:
            await self.lobby_manager.remove_member(self.lobby_id, interaction.user.id)
        except DeletedLobby:
            await self.lobby_manager.delete_lobby(self.lobby_id)
            return

        # Update Ready button
        number_filled = len(
            await self.lobby_manager.get_members_status(self.lobby_id, True)
        )
        self.ready.label = f"Ready: {number_filled}"
        await interaction.edit_original_response(view=self)

        # Update lobby embed
        interaction.client.dispatch("update_lobby_embed", self.lobby_id)  # type: ignore

    @button(label="Lock", style=ButtonStyle.danger, custom_id="lock_button")
    async def lock(self, interaction: Interaction, button: Button):
        await interaction.response.defer()
        lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        # Reject interaction if user is not lobby owner
        lobby_owner = await self.lobby_manager.get_member(
            lobby.guild_id, lobby.owner_id
        )
        if interaction.user != lobby_owner:
            # Defer interaction update
            return

        # Update lobby state
        lobby.state = (
            LobbyStates.ACTIVE
            if lobby.state is LobbyStates.LOCKED
            else LobbyStates.LOCKED
        )

        # Send button label
        if lobby.state is LobbyStates.LOCKED:
            button.label = "Unlock"
        else:
            button.label = "Lock"

        await self.lobby_manager.send_update_lock_embed(self.lobby_id)

        await self.lobby_manager.update_lobby(lobby)

        # Update button label
        await interaction.edit_original_response(view=self)

        # Update lobby embed
        interaction.client.dispatch("update_lobby_embed", self.lobby_id)  # type: ignore

    @button(
        label="Change Leader",
        style=ButtonStyle.blurple,
        custom_id="change_leader_button",
    )
    async def change_leader(self, interaction: Interaction, _: Button):
        await interaction.response.defer()

        lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        lobby_owner = await self.lobby_manager.get_member(
            lobby.guild_id, lobby.owner_id
        )

        if interaction.user != lobby_owner:
            return

        options = []
        list_of_users = await self.lobby_manager.get_members(lobby)
        list_of_users.remove(lobby_owner)

        if len(list_of_users) == 0:
            return

        # Get a list of users
        for member_model in list_of_users:
            options.append((member_model.display_name, member_model.id))
        await interaction.followup.send(
            view=OwnerSelectView(self.lobby_id, self.lobby_manager, options),
            ephemeral=True,
        )

    @button(
        label="Edit Descr.",
        style=ButtonStyle.blurple,
        custom_id="edit_description_button",
    )
    async def edit_description(self, interaction: Interaction, _: Button):
        lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        if interaction.user != await self.lobby_manager.get_member(
            lobby.guild_id, lobby.owner_id
        ):
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.lobby_id, self.lobby_manager),
            )

    @button(label="Disband", style=ButtonStyle.blurple, custom_id="disband_button")
    async def disband(self, interaction: Interaction, _: Button):
        lobby = await self.lobby_manager.get_lobby(self.lobby_id)
        member = await self.lobby_manager.get_member(
            lobby.guild_id,
            interaction.user.id,
        )
        if interaction.user.id == member.id:
            await interaction.response.send_modal(
                DeletionConfirmationModal(self.lobby_id, self.lobby_manager)
            )
        else:
            await interaction.response.defer()

    @button(label="Promote", style=ButtonStyle.blurple, custom_id="promote_button")
    async def promote(self, interaction: Interaction, _: Button):

        lobby = await self.lobby_manager.get_lobby(self.lobby_id)

        class PromotionEmbed(Embed):
            def __init__(
                self,
                game_name: str,
                lobby_id: int,
                lobby_manager: LobbyManager,
                interaction: Interaction,
            ):
                super().__init__(
                    title=f"Sponsor Friendly Ad for {game_name}",
                    color=Color.dark_orange(),
                )
                self.lobby_id = lobby_id
                self.lobby_manager = lobby_manager
                self.interaction = interaction

            async def create(self, lobby: LobbyModel) -> None:
                assert lobby.lobby_channel_id is not None
                channel = await self.lobby_manager.get_channel(
                    lobby.guild_id, lobby.lobby_channel_id
                )
                self.description = f"Click on lobby <#{channel.id}> to join!"

                lobby_size = len(lobby.member_lobbies)
                game_size = lobby.game_size
                description = lobby.description

                game = await self.lobby_manager.get_game(lobby.game_id)

                if description:
                    self.add_field(
                        name="Description:",
                        value=f"⠀⠀⠀⠀⤷  {description}",
                    )
                self.add_field(
                    name="Remaining Space:",
                    value=f"⠀⠀⠀⠀⤷  {game_size - lobby_size} slot(s)",
                    inline=False,
                )
                if game.icon_url:
                    self.set_thumbnail(url=game.icon_url)

        # If user is not lobby owner, defer interaction
        await interaction.response.defer()
        if interaction.user != await self.lobby_manager.get_member(
            lobby.guild_id, lobby.owner_id
        ):
            return
        # If last promotion was older than 10 minutes, defer interaction
        if not await self.lobby_manager.can_promote(lobby):
            return

        is_full = await self.lobby_manager.is_full(self.lobby_id)

        if is_full:
            return

        game = await self.lobby_manager.get_game(lobby.game_id)
        # If the lobby is not full, promote
        original_channel = await self.lobby_manager.get_channel(
            lobby.guild_id, lobby.original_channel_id
        )

        if lobby.last_promotion_message_id:
            last_message = await self.lobby_manager.get_message(
                lobby.guild_id,
                lobby.original_channel_id,
                lobby.last_promotion_message_id,
            )
            # If there was an older promotion, delete it
            await last_message.delete()

        promotional_embed = PromotionEmbed(
            game_name=game.name,
            lobby_id=self.lobby_id,
            lobby_manager=self.lobby_manager,
            interaction=interaction,
        )
        await promotional_embed.create(lobby)

        message = await original_channel.send(
            content=f"<@&{game.role}>" if game.role else None, embed=promotional_embed
        )
        lobby.last_promotion_message_id = message.id
        lobby.last_promotion_datetime = datetime.now(UTC)
        await self.lobby_manager.update_lobby(lobby)


class LobbyCog(commands.GroupCog, group_name="lobby"):
    def __init__(self, bot: commands.Bot, lobby_manager: LobbyManager):
        self.bot = bot
        self.lobby_manager = lobby_manager
        self.logger = set_logger("lobby_cog")
        self.scheduled_clean_up_time = scheduled_clean_up_time
        print("LobbyCog loaded")
        # Start tasks
        self.lobby_cleanup.start()
        self.hydrate_cache.start()
        print(self.get_lobby_cleanup_status())

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        embed = None
        if isinstance(error, ServerConnectionException):
            self.logger.error(error)
        elif isinstance(error, app_commands.errors.CheckFailure):
            try:
                lobby = await self.lobby_manager.get_lobby_by_owner_id(
                    interaction.user.id
                )
                lobby_mention = await self.lobby_manager.lobby_id_to_thread_mention(
                    lobby.id
                )
                embed = Embed(
                    title="Error",
                    description=f"Please use this command in your lobby thread! \
                        {lobby_mention}",
                    color=Color.red(),
                )
            finally:
                if embed:
                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )
        elif isinstance(error, (ThreadChannelNotFound, LobbyChannelNotFound)):
            self.logger.error("Channel ID not found in Lobby: %s", type(error))
        elif isinstance(error, MessageNotFound):
            self.logger.error("Channel ID not found in Lobby: %s", type(error))
        else:
            self.logger.error(error)

    @tasks.loop(
        count=None,
        reconnect=True,
        time=scheduled_clean_up_time,
    )
    async def lobby_cleanup(self):
        """Cleans up lobbies every 5am NZT"""
        lobbies = await self.lobby_manager.get_all_lobbies()
        for lobby in lobbies:
            await self.lobby_manager.get_channel(
                lobby.guild_id, lobby.lobby_channel_id
            )
            await self.lobby_manager.delete_lobby(lobby_id=lobby.id, clean_up=True)

    @lobby_cleanup.before_loop
    async def before_lobby_cleanup(self):
        await self.bot.wait_until_ready()

    def get_lobby_cleanup_status(self):
        running_status = self.lobby_cleanup.is_running()
        next_run_time = datetime.combine(datetime.now(tz=ZoneInfo("Pacific/Auckland")).date(), self.scheduled_clean_up_time)

        if next_run_time < datetime.now(tz=ZoneInfo("Pacific/Auckland")):
            next_run_time += timedelta(days=1)

        status_message = (
            f"=== Lobby Clean Up Task Status ===\n"
            f"Lobby cleanup task is {'running' if running_status else 'not running'}.\n"
            f"Next scheduled run time: {next_run_time.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
            f"======\n"
        )
        return status_message

    # Custom listeners for tasks
    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""
        try:
            lobby = await self.lobby_manager.get_lobby(lobby_id)
            try:
                # If the game or number isn't chosen, return
                game = await self.lobby_manager.get_game(lobby.game_id)
                if game.max_size is None:
                    return
            except AttributeError:
                return
            assert lobby.embed_message_id is not None
            assert lobby.queue_message_id is not None
            assert lobby.lobby_channel_id is not None
            embed_message = await self.lobby_manager.get_message(
                lobby.guild_id, lobby.lobby_channel_id, lobby.embed_message_id
            )
            queue_embed_message = await self.lobby_manager.get_message(
                lobby.guild_id, lobby.lobby_channel_id, lobby.queue_message_id
            )
            if embed_message is None and queue_embed_message is None:
                await self.lobby_manager.initialise_lobby_embed(lobby_id)

            list_of_members = await self.lobby_manager.get_members_status(
                lobby_id, True
            )
            list_of_member_int = [member.member_id for member in list_of_members]

            game = await self.lobby_manager.get_game(lobby.game_id)

            # Update the lobby embed
            await LobbyEmbedManager.update_lobby_embed(
                lobby_id=lobby_id,
                owner=await self.lobby_manager.get_member(
                    lobby.guild_id, lobby.owner_id
                ),
                description=lobby.description,
                state=lobby.state,
                is_full=await self.lobby_manager.is_full(lobby_id),
                members=await self.lobby_manager.get_members(lobby),
                member_ready=list_of_member_int,
                game_name=game.name,
                game_size=lobby.game_size,
                message=embed_message,
            )
            # Update the queue embed
            await LobbyEmbedManager.update_queue_embed(
                queue_members=await self.lobby_manager.get_queue_members(lobby_id),
                message=queue_embed_message,
            )
        except LobbyNotFound:
            self.logger.info("Lobby with ID: %s not found. Skipping embeds update....")

    @update_lobby_embed.before_loop
    async def before_update_lobby_embed(self):
        # Add a delay to bulk edit, rate limit to update embed is 5 per 5 seconds
        await asyncio.sleep(2)

    @commands.Cog.listener()
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @tasks.loop(count=1, reconnect=True)
    async def hydrate_cache(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                # Hydrate game cache. Function implicitly caches.
                await self.lobby_manager.get_games_by_guild_id(guild.id)
            except GamesNotFound:
                self.logger.info(f"Guild with ID: {guild.id} has no games, skipping...")
                continue
        # Hydrate lobby cache
        lobbies = await self.lobby_manager.get_all_lobbies()
        # Register persistent views per lobby on restart
        for lobby in lobbies:
            # Construct button view
            self.bot.add_view(
                view=ButtonView(
                    lobby_id=lobby.id,
                    lobby_manager=self.lobby_manager,
                ),
                message_id=lobby.embed_message_id,
            )
            if lobby.last_deletion_message_id is not None:
                lobby.last_deletion_datetime = datetime.now(UTC)
                message = await self.lobby_manager.get_message(
                    guild_id=lobby.guild_id,
                    channel_id=lobby.history_thread_id,
                    message_id=lobby.last_deletion_message_id,
                )
                if message is None:
                    continue
                try:
                    await message.delete()
                except NotFound:
                    pass
                await self.lobby_manager.send_deletion_message(
                    lobby_id=lobby.id,
                    view=DeletionButtonView(
                        lobby_id=lobby.id,
                        lobby_manager=self.lobby_manager,
                        bot=self.bot,
                    ),
                )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if member.bot is True:
            return
        elif before.channel is None:
            await self.lobby_manager.set_has_joined_vc(member.id)
        elif after.channel is None:
            is_in_lobby, lobby_id = await self.lobby_manager.is_member_in_lobbies(
                member.id
            )
            if not is_in_lobby:
                return
            if not lobby_id:
                raise LobbyNotFound
            if (lobby_cache.get(str(lobby_id))).state is LobbyStates.PENDING_DELETION:
                return
            if await self.lobby_manager.is_full(
                lobby_id
            ) and await self.lobby_manager.is_lobby_in_vc(lobby_id):
                view = DeletionButtonView(
                    lobby_id=lobby_id,
                    lobby_manager=self.lobby_manager,
                    bot=self.bot,
                )
                await self.lobby_manager.send_deletion_message(lobby_id, view)

    @app_commands.command(description="Create lobby through UI", name="create")
    async def create_lobby(
        self,
        interaction: Interaction,
        game: app_commands.Transform[int, GameTransformer],
        size: app_commands.Transform[int, NumberTransformer],
        description: app_commands.Range[str, None, 50] | None,
    ):
        """Creates a lobby through UI command"""

        await interaction.response.defer()
        assert interaction.guild is not None
        lobby_category_channel = utils.get(interaction.guild.channels, name="Lobbies")

        if not lobby_category_channel:
            print("Lobby Category Channel does not exist, creating one...")
            lobby_category_channel = await interaction.guild.create_category_channel(
                "Lobbies"
            )

        # Check if user has created a lobby previously.
        try:
            lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        except LobbyNotFound:
            self.logger.info(
                "No lobby found under ID: %s, continuing lobby creation.",
                interaction.user.id,
            )
            assert isinstance(lobby_category_channel, CategoryChannel)
            assert isinstance(interaction.channel, TextChannel)

            lobby = await self.lobby_manager.create_lobby(
                original_channel_id=interaction.channel.id,
                guild_id=interaction.guild.id,
                guild_name=interaction.guild.name,
                owner_id=interaction.user.id,
                game_id=game,
                max_size=size,
                description=description if description else "",
            )

            game_model = await self.lobby_manager.get_game(game)

            # Create new text channel
            lobby_channel = await interaction.guild.create_text_channel(
                name=f"Lobby {str(lobby.id)}",
                category=lobby_category_channel,
                topic=game_model.name,
                overwrites={
                    interaction.guild.default_role: PermissionOverwrite(
                        send_messages=False
                    ),
                },
            )

            lobby.lobby_channel_id = lobby_channel.id

            embed = Embed(
                title=f"{interaction.user.display_name} created a lobby ✨",
                description=f"Click <#{lobby_channel.id}> to join the lobby",
                color=Color.green(),
            )

            game_size = size if size else "❓"
            game_model = await self.lobby_manager.get_game(game)
            embed.add_field(
                name=f"{game_model.name}",
                value=f"⠀⠀⠀⠀⤷ {game_size} slots",
            )

            embed.add_field(
                name="Description",
                value=f"⠀⠀⠀⠀⤷  {description}",
                inline=False,
            )
            # Add thumbnail if set
            if game_model.icon_url:
                embed.set_thumbnail(url=game_model.icon_url)

            # Promote to role for free on lobby creation
            role: int | None = None
            if game_model.role is not None:
                role = self.lobby_manager.role_id_to_mention(game_model.role)

            # Create embed to redirect user to the new lobby channel
            await interaction.followup.send(
                content=role,
                embed=embed,
            )

            # Create thread for client logging
            thread_message = await lobby_channel.send(
                embed=Embed(title="✍ Lobby History & Chat")
            )
            thread = await lobby_channel.create_thread(
                name="Lobby History & Chat Thread", message=thread_message
            )

            lobby.history_thread_id = thread.id
            lobby = await self.lobby_manager.update_lobby(lobby)

            await self.lobby_manager.initialise_lobby_embed(lobby.id)

            self.bot.dispatch("update_lobby_embed", lobby.id)

            # Query if owner is connected to a voice channel
            owner_voice_state = interaction.user.voice
            if owner_voice_state is None:
                return
            elif owner_voice_state.channel is not None:
                   await self.lobby_manager.set_has_joined_vc(interaction.user.id)
        else:
            await interaction.followup.send(
                "You have already an owner of a lobby!", ephemeral=True
            )

    @app_commands.command(description="Add game to the lobby module", name="gameadd")
    async def add_game(
        self,
        interaction: Interaction,
        game_name: str,
        max_size: int,
        role: Role | None,
        icon_url: str | None,
    ):
        """Adds a game to the lobby module"""

        # Add the game to the list
        await interaction.response.defer()
        assert interaction.guild is not None

        game = await self.lobby_manager.create_game(
            game_name=game_name,
            guild_id=interaction.guild.id,
            max_size=max_size,
            role_id=None if role is None else role.id,
            icon_url=icon_url,
        )

        # Send message to the user
        await interaction.followup.send(
            f"Game {game.name} added with {game.id}!", ephemeral=True
        )

    @app_commands.command(
        description="Remove game from the lobby module", name="gameremove"
    )
    async def remove_game(
        self,
        interaction: Interaction,
        game: app_commands.Transform[int, GameTransformer],
    ):
        """Removes a game from the lobby module"""
        # Check if the game exists

        assert isinstance(game, int)

        game_model = await self.lobby_manager.get_game(int(game))
        # If game not found.
        if game_model is None:
            await interaction.response.send_message(
                "The game given does not exist!", ephemeral=True
            )
            return

        try:
            await self.lobby_manager.remove_game(game)
            await interaction.response.send_message(
                f"Failed to remove game: {game_model.name} with id {game_model.id}!",
                ephemeral=True,
            )
        except DeletedGame:
            await interaction.response.send_message(
                f"Game {game_model.name} with id {game_model.id} removed!",
                ephemeral=True,
            )

    @app_commands.command(description="List all games", name="listgames")
    async def list_games(self, interaction: Interaction):
        """Lists all games"""
        # Check if the game exists
        assert interaction.guild is not None
        try:
            games = await self.lobby_manager.get_games_by_guild_id(interaction.guild.id)
        except GamesNotFound:
            await interaction.response.send_message(
                "There are no games!", ephemeral=True
            )
            return

        embed = Embed(
            title=f"Registered Games on {interaction.guild.name}",
            color=Color.green(),
        )
        if games is None:
            await interaction.response.send_message(
                "There are no games!", ephemeral=True
            )
        for game in games:
            role = interaction.guild.get_role(game.role) if game.role else None
            link = f"[Click here to view]({game.icon_url})" if game.icon_url else "None"
            embed.add_field(
                name=game.name.upper(),
                value=f"""⠀⠀⤷ **ID:** {game.id}
                    ⠀⠀⠀⠀⤷ **Max Size:** {game.max_size}
                    ⠀⠀⠀⠀⤷ **Role:** {role.mention if role else "None"}
                    ⠀⠀⠀⠀⤷ **Icon URL:** {link}""",
                inline=False,
            )
        # Send message to the user
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        description="Lobby Owner: Add user to the lobby", name="userjoin"
    )
    @is_lobby_thread()
    async def add_user(self, interaction: Interaction, user: Member):
        """Adds a user to the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                "There are no lobbies!", ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        try:
            lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        except LobbyNotFound:
            await interaction.response.send_message(
                "You are not an owner of a lobby!", ephemeral=True
            )
            return

        # Check if user is already in the lobby
        if await self.lobby_manager.has_joined(lobby.id, user.id):
            await interaction.response.send_message(
                f"User {user.display_name} is already in the lobby!", ephemeral=True
            )
            return
        # Check if user is not a bot
        if user.bot:
            await interaction.response.send_message(
                f"User {user.display_name} is a bot! Cannot be added.", ephemeral=True
            )
            return
        await self.lobby_manager.add_member(lobby.id, user.id, owner_added=True)
        await interaction.response.send_message(
            f"User {user.display_name} to be added to lobby {lobby.id}, \
            dispatching request to server!",
            ephemeral=True,
        )
        # Send message to the user
        interaction.client.dispatch("update_lobby_embed", lobby.id)  # type: ignore
        # Check if user is in voice channel
        if user.voice is None:
            return
        elif user.voice.channel is not None:
            await self.lobby_manager.set_has_joined_vc(user.id)

    @app_commands.command(
        description="Lobby Owner: Remove user from the lobby", name="userkick"
    )
    @is_lobby_thread()
    async def remove_user(self, interaction: Interaction, user: Member):
        """Removes a user from the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                "There are no lobbies!", ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        if user == interaction.user:
            await interaction.response.send_message(
                "You cannot remove yourself!", ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        try:
            lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        except LobbyNotFound:
            await interaction.response.send_message(
                "You are not an owner of a lobby!", ephemeral=True
            )
            return
        # Check if user is not in the lobby
        if not await self.lobby_manager.has_joined(lobby.id, user.id):
            await interaction.response.send_message(
                f"User {user.display_name} is not in the lobby!", ephemeral=True
            )
            return
        # Remove user from the lobby
        try:
            await self.lobby_manager.remove_member(
                lobby.id, user.id, owner_removed=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error removing user {user.display_name} from the lobby: {e}",
                ephemeral=True,
            )
            return
        # Send message to the user
        await interaction.response.send_message(
            f"User {user.display_name} to be removed from lobby_id {lobby.id}, \
                dispatching request to server!",
            ephemeral=True,
        )
        interaction.client.dispatch("update_lobby_embed", lobby.id)

    @app_commands.command(
        description="Lobby Owner: Toggle ready for a user in the lobby",
        name="userready",
    )
    @is_lobby_thread()
    async def ready_user(self, interaction: Interaction, user: Member):
        """Toggles ready for a user in the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                "There are no lobbies!", ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        try:
            lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        except LobbyNotFound:
            await interaction.response.send_message(
                "You are not the owner of a lobby!", ephemeral=True
            )
            return
        # Check if user is in the lobby
        if not await self.lobby_manager.has_joined(lobby.id, user.id):
            await interaction.response.send_message(
                f"User {user.display_name} is not in the lobby!", ephemeral=True
            )
            return
        try:
            # Toggle ready for user in the lobby
            is_ready = await self.lobby_manager.set_member_state(
                lobby.id, user.id, owner_set=True
            )
        except (MemberNotFound, Exception):
            await interaction.response.send_message(
                f"User {user.display_name} not in the lobby or an error has occurred!",
                ephemeral=True,
            )
            return
        # Send message to the user
        await interaction.response.send_message(
            f'User {user.display_name} is now {"ready" if is_ready else "not ready"}!',
            ephemeral=True,
        )

        interaction.client.dispatch("update_lobby_embed", lobby.id)


async def setup(bot: commands.Bot):


    lobby_embed_manager = LobbyEmbedManager()
    session_manager = ClientSessionManager()
    api_manager = LobbyApi(session_manager)

    lobby_manager = LobbyManager(
        api_manager=api_manager,
        bot=bot,
        embed_manager=lobby_embed_manager,
        transformer_cache=transformer_cache,
        lobby_cache=lobby_cache,
    )

    await bot.add_cog(LobbyCog(bot, lobby_manager))


async def teardown(bot: commands.Bot):
    lobby_cog = bot.get_cog("LobbyCog")
    transformer_cache.clear()
    lobby_cache.clear()
    if lobby_cog:
        # await cog.lobby_manager.close()
        await bot.remove_cog(lobby_cog.__cog_name__)
    else:
        raise Exception("LobbyCog not found!")
