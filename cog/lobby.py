import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    Embed,
    Interaction,
    Member,
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
from api.api_error import GamesNotFound

from api.lobby_api import LobbyApi
from api.models import LobbyModel
from api.session_manager import ClientSessionManager
from cog.classes.lobby.lobby_cache import LobbyCache
from cog.classes.lobby.transformer_error import GameTransformError, NumberTransformError
from cog.classes.lobby.transformer_cache import TransformerCache
from cog.classes.utils import set_logger
from embeds.lobby_embed import LobbyEmbedManager
from exceptions.lobby_exceptions import (
    DeletedGame,
    DeletedLobby,
    LobbyNotFound,
    MemberNotFound,
)
from manager.lobby_service import LobbyManager

transformer_cache = TransformerCache()
lobby_cache = LobbyCache()


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
            game_id = interaction.namespace["game"]
            games = transformer_cache.get(str(interaction.guild.id))
            if games is None:
                raise NumberTransformError("There are no games in this server")
            # Find the GameModel with the matching game_id
            game_model = next((game for game in games if game.id == int(game_id)), None)
            if game_model is None:
                raise ValueError
            max_size = game_model.max_size
            number = int(argument)
            if number < 2:
                return 2
            elif number > max_size:
                return max_size
            else:
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
                        if str(i).startswith(str(value)):
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
            lobby.guild_id, lobby.original_channel_id
        )
        await self.lobby_manager.delete_lobby(
            lobby_id=self.lobby_id, reason=self.reason.value
        )
        await lobby_channel.delete()


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


class ButtonView(View):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__(timeout=None)
        self.id = str(lobby_id)
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    @button(label="Join", style=ButtonStyle.green, custom_id="join_button")
    async def join_button(self, interaction: Interaction, button: Button):
        # Check if the member has already joined
        await interaction.response.defer()
        if await self.lobby_manager.has_joined(self.lobby_id, interaction.user.id):
            return

        await self.lobby_manager.add_member(self.lobby_id, interaction.user.id)

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
        is_locked = (await self.lobby_manager.get_lobby(self.lobby_id)).is_locked
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
        is_locked = lobby.is_locked
        lobby.is_locked = not is_locked
        await self.lobby_manager.update_lobby(lobby)

        # Send button label
        if lobby.is_locked:
            button.label = "Unlock"
        else:
            button.label = "Lock"
            # TODO: Make this an endpoint for the backend
            # await self.lobby_manager.move_queue_members(self.lobby_id)

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
        if interaction.user == await self.lobby_manager.get_member(
            lobby.guild_id, self.lobby_id
        ):
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
        lobby.last_promotion_datetime = datetime.now()
        await self.lobby_manager.update_lobby(lobby)


class LobbyCog(commands.GroupCog, group_name="lobby"):
    def __init__(self, bot: commands.Bot, lobby_manager: LobbyManager):
        self.bot = bot
        self.lobby_manager = lobby_manager
        self.logger = set_logger("lobby_cog")
        print("LobbyCog loaded")
        # Start tasks
        self.lobby_cleanup.start()
        self.hydrate_cache.start()

    async def cog_app_command_error(self, interaction: Interaction, error: Exception):
        embed = None
        if isinstance(error, app_commands.errors.CheckFailure):
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
            except LobbyNotFound:
                embed = Embed(
                    title="Error",
                    description="You are not an owner of any lobby! \
                        Also wrong channel to use this command!",
                    color=Color.red(),
                )
            finally:
                if embed:
                    await interaction.response.send_message(
                        embed=embed,
                        ephemeral=True,
                    )
        elif isinstance(error, GameTransformError):
            embed = Embed(
                title=error.args,
                description="Please use an option from the autocomplete list!",
                color=Color.red(),
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
        elif isinstance(error, NumberTransformError):
            embed = Embed(
                title=error.args,
                description="Please input numbers only!",
                color=Color.red(),
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

    @tasks.loop(
        count=None,
        reconnect=True,
        time=datetime(
            2021, 1, 1, 5, 0, 0, 0, tzinfo=ZoneInfo("Pacific/Auckland")
        ).timetz(),
    )
    async def lobby_cleanup(self):
        """Cleans up lobbies every 5am NZT"""
        lobbies = await self.lobby_manager.get_all_lobbies()
        for lobby in lobbies:
            lobby_channel = await self.lobby_manager.get_channel(
                lobby.guild_id, lobby.id
            )
            await lobby_channel.delete()
            await self.lobby_manager.delete_lobby(lobby_id=lobby.id, clean_up=True)

    @lobby_cleanup.before_loop
    async def before_lobby_cleanup(self):
        await self.bot.wait_until_ready()

    # Custom listeners for tasks
    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""

        lobby = await self.lobby_manager.get_lobby(lobby_id)
        # If the game or number isn't chosen, return
        try:
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

        list_of_members = await self.lobby_manager.get_members_status(lobby_id, True)
        list_of_member_int = [member.member_id for member in list_of_members]

        # Update the lobby embed
        await LobbyEmbedManager.update_lobby_embed(
            lobby_id=lobby_id,
            owner=await self.lobby_manager.get_member(lobby.guild_id, lobby.owner_id),
            description=lobby.description,
            is_locked=lobby.is_locked,
            is_full=await self.lobby_manager.is_full(lobby_id),
            members=await self.lobby_manager.get_members(lobby),
            member_ready=list_of_member_int,
            game_size=lobby.game_size,
            message=embed_message,
        )
        # Update the queue embed
        await LobbyEmbedManager.update_queue_embed(
            queue_members=await self.lobby_manager.get_queue_members(lobby_id),
            message=queue_embed_message,
        )

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
        if lobbies:
            for lobby in lobbies:
                # Construct button view
                self.bot.add_view(
                    view=ButtonView(
                        lobby_id=lobby.id,
                        lobby_manager=self.lobby_manager,
                    ),
                    message_id=lobby.embed_message_id,
                )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        if member.bot is False:
            if before.channel is None:
                await self.lobby_manager.set_has_joined_vc(member.id)
            # if after.channel is None:
            #     await self.lobby_manager.set_has_left_vc(member.id)
            # TODO: Trigger a deletion

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
        lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        if lobby:
            await interaction.followup.send(
                "You have already an owner of a lobby!", ephemeral=True
            )
            return

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

        # Create new text channel
        lobby_channel = await interaction.guild.create_text_channel(
            name=f"Lobby {str(lobby.id)}",
            category=lobby_category_channel,
            overwrites={
                interaction.guild.default_role: PermissionOverwrite(
                    send_messages=False
                ),
            },
        )

        lobby.lobby_channel_id = lobby_channel.id
        # TODO: Move into embed manager class
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

        # Create embed to redirect user to the new lobby channel
        await interaction.followup.send(
            embed=embed,
        )

        # Create thread for logging
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
        games = await self.lobby_manager.get_games_by_guild_id(interaction.guild.id)
        if not games:
            await interaction.response.send_message(
                "There are no games!", ephemeral=True
            )
            return

        embed = Embed(
            title=f"Registered Games on {interaction.guild.name}",
            color=Color.green(),
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
        lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        if not lobby:
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
        interaction.client.dispatch("update_lobby_embed", lobby_id)  # type: ignore

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
        lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        if not lobby:
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
        lobby = await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
        if not lobby:
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
