import asyncio
import discord
from collections.abc import Sequence
from discord.ext import commands, tasks
from discord import Client, Interaction, app_commands
from discord.ui import View, TextInput
from embeds.game_embed import GameEmbedManager

from embeds.lobby_embed import LobbyEmbedManager
from exceptions.lobby_exceptions import LobbyNotFound, MemberNotFound
from manager.lobby_service import LobbyManager
from manager.game_service import GameManager

from repository.tables import GameModel, LobbyModel
from repository.game_repo import GamePostgresRepository
from repository.lobby_repo import LobbyPostgresRepository
from repository.db_config import async_session

# Predicate for commands


def is_lobby_thread():
    """Checks if the interaction is in a lobby thread"""
    def predicate(interaction: discord.Interaction) -> bool:
        assert interaction.channel is not None
        return isinstance(interaction.channel, discord.threads.Thread)
    return app_commands.check(predicate)


class GameTransformError(app_commands.AppCommandError):
    pass


class NumberTransformError(app_commands.AppCommandError):
    pass


class GameTransformer(app_commands.Transformer):

    def __init__(self):
        self._game_manager = None

    def get_game_manager(self, interaction: discord.Interaction):
        if self._game_manager is None:
            self._game_manager = GameManager(
                repository=GamePostgresRepository(async_session),
                embed_manager=GameEmbedManager(),
                bot=interaction.client
            )
        return self._game_manager

    async def transform(self, interaction: discord.Interaction, argument: str) -> int:
        assert interaction.guild is not None
        game_manager = self.get_game_manager(interaction)
        game_cache = await game_manager.get_all_games_by_guild_id(interaction.guild.id)
        try:
            value = int(argument)
            for game in game_cache:
                if value == game.id:
                    return game.id
            else:
                raise GameTransformError(f"Game_id: {argument} not found")
        except ValueError:
            raise GameTransformError(f"Game_id: {argument} not found")

    async def autocomplete(
        self,
        interaction: Interaction,
        value: int | float | str,
        /
    ) -> list[app_commands.Choice[int | float | str]]:
        assert interaction.guild is not None
        list_of_options: list[app_commands.Choice[int | float | str]] = []

        game_manager = self.get_game_manager(interaction)
        game_cache = await game_manager.get_all_games_by_guild_id(interaction.guild.id)
        # If there are no games available, return an empty list
        if len(game_cache) == 0:
            return list_of_options
        # If nothing is inputted, return all games
        if value == "":
            for game in game_cache:
                list_of_options.append(
                    app_commands.Choice(
                        name=game.name,
                        value=str(game.id)
                    )
                )
        else:
            # If there is an input, return all games that start with the input
            for game in game_cache:
                if game.name.lower().startswith(str(value).lower()):
                    list_of_options.append(
                        app_commands.Choice(
                            name=game.name,
                            value=str(game.id)
                        )
                    )
        return list_of_options


class NumberTransformer(app_commands.Transformer):

    def __init__(self):
        self._game_manager = None

    def get_game_manager(self, interaction: discord.Interaction):
        if self._game_manager is None:
            self._game_manager = GameManager(
                repository=GamePostgresRepository(async_session),
                embed_manager=GameEmbedManager(),
                bot=interaction.client
            )
        return self._game_manager

    async def transform(self, interaction: discord.Interaction, argument: str) -> int:
        assert interaction.guild is not None
        game_manager = self.get_game_manager(interaction)
        try:
            game_id = interaction.namespace["game"]
            max_size = await game_manager.get_max_size(int(game_id))
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
        self,
        interaction: Interaction,
        value: int | float | str,
        /
    ) -> list[app_commands.Choice[int | float | str]]:
        list_of_options: list[app_commands.Choice[int | float | str]] = []
        game_id = interaction.namespace["game"]
        game_manager = self.get_game_manager(interaction)
        if game_id is None:
            return list_of_options
        try:
            max_players = await game_manager.get_max_size(int(game_id))
            if value is None:
                for i in range(1, max_players):
                    list_of_options.append(
                        app_commands.Choice(
                            name=str(i+1),
                            value=str(i+1)
                        )
                    )
            else:
                for i in range(1, max_players):
                    if str(i).startswith(str(value)):
                        list_of_options.append(
                            app_commands.Choice(
                                name=str(i+1),
                                value=str(i+1)
                            )
                        )
            return list_of_options
        except ValueError:
            return []


class DropdownView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        list_of_games: Sequence[GameModel],
        game_manager: GameManager,
        lobby_manager: LobbyManager,
        game_id: int | None = None,
        player_number: int | None = None,
    ):
        super().__init__(timeout=None)

        # Adds the dropdown to our view object
        game_result: list[GameModel] = [
            game for game in list_of_games if game.id == game_id]

        if game_result == []:
            self.add_item(
                GameDropdown(
                    lobby_id=lobby_id,
                    games=list_of_games,
                    game_manager=game_manager,
                    lobby_manager=lobby_manager,
                )
            )
            return

        self.add_item(
            GameDropdown(
                lobby_id=lobby_id,
                games=list_of_games,
                game_manager=game_manager,
                lobby_manager=lobby_manager,
                placeholder=game_result[0].name
            )
        )

        if player_number is not None:
            self.add_item(
                NumberDropdown(
                    lobby_id=lobby_id,
                    lobby_manager=lobby_manager,
                    game_manager=game_manager,
                    bot=game_manager.bot,
                    number=player_number,
                    placeholder=str(player_number)
                )
            )
        elif player_number is None:
            self.add_item(
                NumberDropdown(
                    lobby_id=lobby_id,
                    lobby_manager=lobby_manager,
                    game_manager=game_manager,
                    bot=game_manager.bot,
                    number=game_result[0].max_size,
                )
            )


class GameDropdown(discord.ui.Select):
    """A select dropdown for a list of games."""

    def __init__(
        self,
        lobby_id: int,
        games: Sequence[GameModel],
        game_manager: GameManager,
        lobby_manager: LobbyManager,
        placeholder: str = "Choose your game..."
    ):
        # Set the options that will be presented inside the dropdown
        options: list[discord.SelectOption] = []
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
        self.game_manager = game_manager
        self.custom_id = f"game_dropdown: {lobby_id}"

        # Create select dropdown options from file.
        for game in games:
            options.append(
                discord.SelectOption(
                    label=game.name,
                    value=str(game.id),
                )
            )

        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    async def callback(self, interaction: discord.Interaction):
        lobby_owner = await self.lobby_manager.get_lobby_owner(self.lobby_id)

        await interaction.response.defer()
        if not interaction.user == lobby_owner:
            return

        # Remove NumberDropdown for an updated one
        view: View = self.view  # type: ignore
        if (len(view.children) != 1):
            view.remove_item(view.children[1])

        # Save selected game code in state.
        game_id = await self.lobby_manager.set_game_id(
            self.lobby_id,
            int(interaction.data['values'][0])  # type: ignore
        )
        assert game_id is not None

        number = await self.game_manager.get_max_size(game_id=game_id)

        dropdown: GameDropdown = view.children[0]  # type: ignore
        for option in dropdown.options:
            if option.value == str(game_id):
                dropdown.placeholder = option.label
                break

        view.add_item(
            NumberDropdown(
                lobby_id=self.lobby_id,
                lobby_manager=self.lobby_manager,
                game_manager=self.game_manager,
                bot=interaction.client,
                number=number
            )
        )
        assert interaction.message is not None
        # Respond to interaction with updated view
        await interaction.message.edit(view=self.view)


class NumberDropdown(discord.ui.Select):
    # A select dropdown for a list of numbers.
    def __init__(
        self,
        lobby_id: int,
        lobby_manager: LobbyManager,
        game_manager: GameManager,
        bot: Client,
        number: int,
        placeholder: str = "Choose your number...",
    ):
        options = [
            discord.SelectOption(
                label=str(x + 1)) for x in range(1, number)
        ]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
        )
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager
        self.game_manager = game_manager
        self.bot = bot

        self.custom_id = f"number_dropdown: {lobby_id}"
        # Set the options that will be presented inside the dropdown

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()

        # Reject interaction if user is not lobby owner
        if interaction.user != await self.lobby_manager.get_lobby_owner(self.lobby_id):
            return

        game_size = await self.lobby_manager.set_gamesize(
            self.lobby_id,
            int(interaction.data['values'][0])  # type: ignore
        )

        view: View = self.view  # type: ignore
        # Set placeholder of dropdown to reflect selected value
        dropdown: NumberDropdown = view.children[1]  # type: ignore
        dropdown.placeholder = str(game_size)

        assert interaction.message is not None
        # Respond to interaction with updated view
        await interaction.message.edit(
            content="",
            view=self.view
        )

        # Initialise embed and button view that will be updated when lobby state
        self.bot.dispatch('update_lobby_embed', self.lobby_id)


class DescriptionModal(discord.ui.Modal, title='Edit Description'):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__()
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    answer = TextInput(  # type: ignore
        label='Edit Description',
        style=discord.TextStyle.paragraph,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self.lobby_manager.set_description(self.lobby_id, self.answer.value)
        interaction.client.dispatch('update_lobby_embed', self.lobby_id) # type: ignore


class DeletionConfirmationModal(
    discord.ui.Modal,
    title='Are you sure? Reason optional.'
):
    def __init__(self, lobby_id: int, lobby_manager: LobbyManager):
        super().__init__()
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager

    reason = TextInput(  # type: ignore
        label='Reason',
        max_length=150,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()

        lobby_channel = await self.lobby_manager.get_lobby_channel(self.lobby_id)
        await self.lobby_manager.delete_lobby(
            lobby_id=self.lobby_id,
            reason=self.reason.value
        )
        await lobby_channel.delete()


class OwnerSelectView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        lobby_manager: LobbyManager,
        list_of_users: list[tuple[str, int]]
    ):
        super().__init__()
        self.list_of_users = list_of_users
        self.add_item(
            self.OwnerDropdown(
                lobby_id,
                list_of_users,
                lobby_manager
            )
        )

    class OwnerDropdown(discord.ui.Select):
        def __init__(
            self,
            lobby_id: int,
            list_of_users: list[tuple[str, int]],
            lobby_manager: LobbyManager
        ):
            options = []

            for user in list_of_users:
                options.append(discord.SelectOption(
                    label=user[0],
                    value=str(user[1])
                ))

            super().__init__(
                placeholder='Choose new owner...',
                min_values=1,
                max_values=1,
                options=options
            )
            self.lobby_id = lobby_id
            self.lobby_manager = lobby_manager

        async def callback(self, interaction: discord.Interaction):
            lobby_owner = await self.lobby_manager.get_lobby_owner(self.lobby_id)
            await interaction.response.defer()
            if interaction.user != lobby_owner:
                return

            assert interaction.guild is not None
            member = interaction.guild.get_member(int(self.values[0]))
            assert member is not None
            await self.lobby_manager.switch_owner(self.lobby_id, member.id)
            await self.lobby_manager.get_lobby_owner(self.lobby_id)
            interaction.client.dispatch(  # type: ignore
                'update_lobby_embed', self.lobby_id)

            # Disable view after selection
            if self.view is not None:
                self.view.stop()


class ButtonView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        lobby_manager: LobbyManager,
        game_manager: GameManager
    ):
        super().__init__(timeout=None)
        self.id = str(lobby_id)
        self.lobby_id = lobby_id
        self.lobby_manager = lobby_manager
        self.game_manager = game_manager

    @discord.ui.button(
        label='Join',
        style=discord.ButtonStyle.green,
        custom_id='join_button'
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        # Check if the member has already joined
        await interaction.response.defer()
        if await self.lobby_manager.has_joined(self.lobby_id, interaction.user.id):
            return

        # Check if lobby full
        is_full = await self.lobby_manager.is_full(self.lobby_id)
        # Check if lobby is locked
        is_locked = await self.lobby_manager.get_is_lobby_lock(self.lobby_id)
        # Check if the lobby is locked
        if is_locked is True or is_full:
            await self.lobby_manager.add_member_queue(
                self.lobby_id,
                interaction.user.id
            )
        else:
            await self.lobby_manager.add_member(self.lobby_id, interaction.user.id)

        interaction.client.dispatch('update_lobby_embed', self.lobby_id)  # type: ignore

    @discord.ui.button(
        label="Ready",
        style=discord.ButtonStyle.green,
        custom_id='ready_button'
    )
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()
        # Reject interaction if user is not in lobby
        has_joined = await self.lobby_manager.has_joined(
            self.lobby_id,
            interaction.user.id
        )
        if not has_joined:
            # Defer interaction update
            return

        # Reject interaction if lobby is locked
        is_locked = await self.lobby_manager.get_is_lobby_lock(self.lobby_id)
        if is_locked:
            # Defer interaction update
            return

        # Update member state
        await self.lobby_manager.set_member_state(
            self.lobby_id,
            interaction.user.id
        )

        # Update button
        number_filled = len(await self.lobby_manager.get_members_ready(self.lobby_id))
        button.label = f"Ready: {number_filled}"
        await interaction.edit_original_response(view=self)

        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)  # type: ignore

    @discord.ui.button(
        label="Leave",
        style=discord.ButtonStyle.red,
        custom_id='leave_button'
    )
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # Check if user is in lobby
        if not await self.lobby_manager.has_joined(self.lobby_id, interaction.user.id):
            return

        lobby_owner = await self.lobby_manager.get_lobby_owner(self.lobby_id)

        # Delete lobby if there is 1 person left
        if await self.lobby_manager.get_member_length(self.lobby_id) == 1:
            lobby_channel = await self.lobby_manager.get_lobby_channel(self.lobby_id)
            await self.lobby_manager.delete_lobby(self.lobby_id)
            await lobby_channel.delete()
            return
        # Remove member from lobby
        elif interaction.user != lobby_owner:
            await self.lobby_manager.remove_member(self.lobby_id, interaction.user.id)
        # Remove user and find new leader
        elif interaction.user == lobby_owner:
            await self.lobby_manager.remove_member(self.lobby_id, interaction.user.id)
            new_owner_id = await self.lobby_manager.search_new_owner(self.lobby_id)
            # Delete if there are no suitable owner candidates
            if new_owner_id is None:
                lobby_channel = await self.lobby_manager.get_lobby_channel(
                    self.lobby_id
                )
                await self.lobby_manager.delete_lobby(self.lobby_id)
                await lobby_channel.delete()
                return
            await self.lobby_manager.switch_owner(self.lobby_id, new_owner_id)

        # Move member to queue when someone leaves
        await self.lobby_manager.move_queue_members(self.lobby_id)

        # Update Ready button
        number_filled = len(await self.lobby_manager.get_members_ready(self.lobby_id))
        self.ready.label = f"Ready: {number_filled}"
        await interaction.edit_original_response(view=self)
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)  # type: ignore

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.danger,
        custom_id='lock_button'
    )
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()
        # Reject interaction if user is not lobby owner
        lobby_owner = await self.lobby_manager.get_lobby_owner(self.lobby_id)
        if interaction.user != lobby_owner:
            # Defer interaction update
            return

        # Update lobby state
        is_locked = await self.lobby_manager.set_is_lobby_locked(self.lobby_id)

        # Send button label
        if is_locked:
            button.label = "Unlock"
        elif not is_locked:
            button.label = "Lock"
            await self.lobby_manager.move_queue_members(self.lobby_id)

        # Update button label
        await interaction.edit_original_response(view=self)

        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id) # type: ignore

    @discord.ui.button(
        label="Change Leader",
        style=discord.ButtonStyle.blurple,
        custom_id='change_leader_button'
    )
    async def change_leader(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        lobby_owner = await self.lobby_manager.get_lobby_owner(self.lobby_id)
        await interaction.response.defer()
        if interaction.user != lobby_owner:
            return

        options = []
        list_of_users = await self.lobby_manager.get_members(self.lobby_id)
        list_of_users.remove(lobby_owner)

        if len(list_of_users) == 0:
            return

        # Get a list of users
        for member_model in list_of_users:
            options.append(
                (member_model.display_name, member_model.id))
        await interaction.edit_original_response(
            view=OwnerSelectView(
                self.lobby_id,
                self.lobby_manager,
                options
            ),
        )

    @discord.ui.button(
        label="Edit Descr.",
        style=discord.ButtonStyle.blurple,
        custom_id='edit_description_button'
    )
    async def edit_description(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user != await self.lobby_manager.get_lobby_owner(self.lobby_id):
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.lobby_id, self.lobby_manager),
            )

    @discord.ui.button(
        label="Disband",
        style=discord.ButtonStyle.blurple,
        custom_id='disband_button'
    )
    async def disband(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        if interaction.user == await self.lobby_manager.get_lobby_owner(self.lobby_id):
            await interaction.response.send_modal(
                DeletionConfirmationModal(self.lobby_id, self.lobby_manager)
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(
        label="Promote",
        style=discord.ButtonStyle.blurple,
        custom_id='promote_button'
    )
    async def promote(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        class PromotionEmbed(discord.Embed):
            def __init__(
                self,
                game_name: str,
                lobby_id: int,
                lobby_manager: LobbyManager,
                interaction: discord.Interaction
            ):
                super().__init__(
                    title=f'Sponsor Friendly Ad for {game_name}',
                    color=discord.Color.dark_orange(),
                )
                self.lobby_id = lobby_id
                self.lobby_manager = lobby_manager
                self.interaction = interaction

            async def create(self):
                channel = await self.lobby_manager.get_lobby_channel(self.lobby_id)
                self.description = f'Click on lobby <#{channel.id}> to join!'
                lobby_size = await self.lobby_manager.get_member_length(self.lobby_id)
                game_size = await self.lobby_manager.get_gamesize(self.lobby_id)
                description = await self.lobby_manager.get_description(self.lobby_id)
                if description:
                    self.add_field(
                        name='Description:',
                        value=f'⠀⠀⠀⠀⤷  {description}',
                    )
                self.add_field(
                    name='Remaining Space:',
                    value=f'⠀⠀⠀⠀⤷  {game_size - lobby_size} slot(s)',
                    inline=False,
                )
                if game_model.icon_url:
                    self.set_thumbnail(url=game_model.icon_url)

        await interaction.response.defer()
        # If user is not lobby owner, defer interaction
        if interaction.user != await self.lobby_manager.get_lobby_owner(self.lobby_id):
            return
        # If last promotion was older than 10 minutes, defer interaction
        if not await self.lobby_manager.can_promote(self.lobby_id):
            return

        is_full = await self.lobby_manager.is_full(self.lobby_id)
        game_model = await self.game_manager.get_game(
            await self.lobby_manager.get_game_id(self.lobby_id)
        )
        # If the lobby is not full, promote
        if not is_full:
            original_channel = await self.lobby_manager.get_original_channel(
                self.lobby_id
            )
            last_message = await self.lobby_manager.get_last_promotion_message(
                self.lobby_id
            )
            # If there was an older promotion, delete it
            if last_message:
                await last_message.delete()
            promotional_embed = PromotionEmbed(
                game_name=game_model.name,
                lobby_id=self.lobby_id,
                lobby_manager=self.lobby_manager,
                interaction=interaction,)
            await promotional_embed.create()
            message = await original_channel.send(
                content=f'<@&{game_model.role}>',
                embed=promotional_embed
            )
            await self.lobby_manager.set_last_promotion_message(
                self.lobby_id,
                message.id
            )


class LobbyCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        lobby_manager: LobbyManager,
        game_manager: GameManager,
    ):

        self.bot = bot
        self.game_manager = game_manager
        self.lobby_manager = lobby_manager
        print('LobbyCog loaded')

    async def cog_app_command_error(
        self,
        interaction: discord.Interaction,
        error: Exception
    ):
        if isinstance(error, discord.app_commands.errors.CheckFailure):
            try:
                lobby_id = await self.lobby_manager.get_lobby_id_by_owner_id(
                    interaction.user.id
                )
                lobby_mention = await self.lobby_manager.lobby_id_to_thread_mention(
                    lobby_id
                )
                embed = discord.Embed(
                    title='Error',
                    description=f'Please use this command in your lobby thread! \
                        {lobby_mention}',
                    color=discord.Color.red()
                )
            except LobbyNotFound:
                embed = discord.Embed(
                    title='Error',
                    description='You are not an owner of any lobby! \
                        Also wrong channel to use this command!',
                    color=discord.Color.red()
                )
            finally:
                await interaction.response.send_message(
                    embed=embed,
                    ephemeral=True,
                )
        elif isinstance(error, GameTransformError):
            embed = discord.Embed(
                title=error.args,
                description='Please use an option from the autocomplete list!',
                color=discord.Color.red()
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )
        elif isinstance(error, NumberTransformError):
            embed = discord.Embed(
                title=error.args,
                description='Please input numbers only!',
                color=discord.Color.red()
            )
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

    # Custom listeners for tasks
    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""

        # If the game or number isn't chosen, return
        try:
            await self.lobby_manager.get_game_id(lobby_id)
            max_size = await self.lobby_manager.get_gamesize(lobby_id)
            if max_size is None:
                return
        except AttributeError:
            return

        embed_message = await self.lobby_manager.get_embed_message(lobby_id)
        queue_embed_message = await self.lobby_manager.get_queue_embed_message(lobby_id)
        if embed_message is None and queue_embed_message is None:
            await self.lobby_manager.initialise_lobby_embed(lobby_id, self.game_manager)

        # Update the lobby embed
        await LobbyEmbedManager.update_lobby_embed(
            lobby_id=lobby_id,
            owner=await self.lobby_manager.get_lobby_owner(lobby_id),
            description=await self.lobby_manager.get_description(lobby_id),
            is_locked=await self.lobby_manager.get_is_lobby_lock(lobby_id),
            is_full=await self.lobby_manager.is_full(lobby_id),
            members=await self.lobby_manager.get_members(lobby_id),
            member_ready=await self.lobby_manager.get_members_ready(lobby_id),
            game_size=await self.lobby_manager.get_gamesize(lobby_id),
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

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(
        self,
        interaction: Interaction,
        game: app_commands.Transform[int, GameTransformer] | None,
        size: app_commands.Transform[int, NumberTransformer] | None,
        description: app_commands.Range[str, None, 50] | None,
    ):
        """Creates a lobby through UI command"""

        await interaction.response.defer()
        assert interaction.guild is not None
        lobby_category_channel = discord.utils.get(
            interaction.guild.channels, name='Lobbies')

        if not lobby_category_channel:
            print('Lobby Category Channel does not exist, creating one...')
            lobby_category_channel = await interaction.guild.create_category_channel(
                'Lobbies'
            )

        # Check if user has created a lobby previously.
        try:
            await self.lobby_manager.get_lobby_by_owner_id(interaction.user.id)
            await interaction.followup.send(
                'You have already an owner of a lobby!',
                ephemeral=True
            )
            return
        except LobbyNotFound:
            # If lobby has not been found, continue
            pass

        assert isinstance(lobby_category_channel, discord.CategoryChannel)

        # Create new text channel
        lobby_channel = await interaction.guild.create_text_channel(
            name=f'{await self.lobby_manager.get_lobby_name()}',
            category=lobby_category_channel,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False
                ),
            }
        )

        embed = discord.Embed(
            title=f'{interaction.user.display_name} created a lobby ✨',
            description=f'Click <#{lobby_channel.id}> to join the lobby',
            color=discord.Color.green(),
        )

        if game is not None:
            game_size = size if size else "❓"
            game_model = await self.game_manager.get_game(game)
            embed.add_field(
                name=f'{game_model.name}',
                value=f'⠀⠀⠀⠀⤷ {game_size} slots',
            )
        if description is not None:
            embed.add_field(
                name='Description',
                value=f'⠀⠀⠀⠀⤷  {description}',
                inline=False,
            )

        # Create embed to redirect user to the new lobby channel
        await interaction.followup.send(
            embed=embed,
        )

        control_panel_message = await lobby_channel.send(
            embed=discord.Embed(
                title='🕹 Control Panel for Lobby Owner'
            )
        )

        game = game if game is not None else None
        number = size if size is not None else None

        lobby_id = await self.lobby_manager.create_lobby(
            control_panel_message_id=control_panel_message.id,
            original_channel_id=interaction.channel.id,  # type: ignore
            lobby_channel_id=lobby_channel.id,
            guild_id=interaction.guild.id,
            guild_name=interaction.guild.name,
            user_id=interaction.user.id,
            game_id=game,
            max_size=number,
            description=description,
        )

        # Create thread for logging
        thread_message = await lobby_channel.send(
            embed=discord.Embed(
                title='✍ Lobby History & Chat'
            )
        )
        thread = await lobby_channel.create_thread(
            name="Lobby History & Chat Thread",
            message=thread_message
        )
        await self.lobby_manager.set_thread(lobby_id, thread.id)

        # Create custom view to hold logic, userid is used to have an instance per user
        view = DropdownView(
            lobby_id=lobby_id,
            list_of_games=await self.game_manager.get_all_games_by_guild_id(
                interaction.guild.id
            ),
            game_manager=self.game_manager,
            lobby_manager=self.lobby_manager,
            game_id=game,
            player_number=size,
        )
        # Message select dropdowns in the channel
        await control_panel_message.edit(view=view)
        self.bot.dispatch('update_lobby_embed', lobby_id)

    @app_commands.command(description="Add game to the lobby module", name='gameadd')
    async def add_game(
        self,
        interaction: Interaction,
        game_name: str,
        role: discord.Role,
        max_size: int,
        icon_url: str | None
    ):
        """Adds a game to the lobby module"""

        # Add the game to the list
        assert interaction.guild is not None

        game_id = await self.game_manager.add_game(
            game_name=game_name,
            guild_name=interaction.guild.name,
            guild_id=interaction.guild.id,
            max_size=max_size,
            role=role.id,
            icon_url=icon_url.strip() if icon_url else None
        )

        # Send message to the user
        await interaction.response.send_message(
            f'Game {game_name} added with {game_id}!',
            ephemeral=True
        )

    @app_commands.command(
        description="Remove game from the lobby module",
        name='gameremove'
    )
    async def remove_game(
        self,
        interaction: Interaction,
        game: app_commands.Transform[int, GameTransformer] | None
    ):
        """Removes a game from the lobby module"""
        # Check if the game exists
        try:
            game_model = await self.game_manager.get_game(int(game)) # type: ignore
        except (ValueError, TypeError):
            # Send message to the user
            await interaction.response.send_message(
                'The game given does not exist!',
                ephemeral=True
            )

        deleted = await self.game_manager.remove_game(int(game)) # type: ignore
        if deleted:
            # Send message to the user
            await interaction.response.send_message(
                f'Game {game_model.name} with id {game_model.id} removed!',
                ephemeral=True
            )
        else:
            # Send message to the user
            await interaction.response.send_message(
                f'Failed to remove {game_model.name} with id: {game_model.id}!',
                ephemeral=True
            )

    @app_commands.command(description="List all games", name='listgames')
    async def list_games(
        self,
        interaction: Interaction
    ):
        """Lists all games"""
        # Check if the game exists
        assert interaction.guild is not None
        games = await self.game_manager.get_all_games_by_guild_id(interaction.guild.id)
        if not games:
            await interaction.response.send_message(
                'There are no games!',
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f'Registered Games on {interaction.guild.name}',
            color=discord.Color.green(),
        )

        for game in games:
            role = interaction.guild.get_role(game.role)
            link = f"[Click here to view]({game.icon_url})" if game.icon_url else "None"
            embed.add_field(
                name=game.name.upper(),
                value=f'''⠀⠀⤷ **ID:** {game.id}
                    ⠀⠀⠀⠀⤷ **Max Size:** {game.max_size}
                    ⠀⠀⠀⠀⤷ **Role:** {role.mention if role else "None"}
                    ⠀⠀⠀⠀⤷ **Icon URL:** {link}''',
                inline=False
            )
        # Send message to the user
        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(
            description="Lobby Owner: Add user to the lobby",
            name='userjoin'
        )
    @is_lobby_thread()
    async def add_user(self, interaction: discord.Interaction, user: discord.Member):
        """Adds a user to the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                'There are no lobbies!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        lobby_id = await self.lobby_manager.get_lobby_id_by_owner_id(
            interaction.user.id
        )
        if not lobby_id:
            await interaction.response.send_message(
                'You are not an owner of a lobby!',
                ephemeral=True
            )
            return
        # Check if user is already in the lobby
        if await self.lobby_manager.has_joined(lobby_id, user.id):
            await interaction.response.send_message(
                f'User {user.display_name} is already in the lobby!',
                ephemeral=True
            )
            return
        # Check if user is not a bot
        if user.bot:
            await interaction.response.send_message(
                f'User {user.display_name} is a bot! Cannot be added.',
                ephemeral=True
            )
            return
        # Add user to the lobby
        is_full = await self.lobby_manager.is_full(lobby_id)
        is_locked = await self.lobby_manager.get_is_lobby_lock(lobby_id)
        if any([is_full, is_locked]):
            await self.lobby_manager.add_member_queue(lobby_id, user.id)
        else:
            await self.lobby_manager.add_member(
                lobby_id,
                user.id,
                owner_added=True
            )
        await interaction.response.send_message(
            f'User {user.display_name} to be added to lobby {lobby_id}, \
            dispatching request to server!',
            ephemeral=True
        )
        # Send message to the user
        interaction.client.dispatch("update_lobby_embed", lobby_id) # type: ignore

    @app_commands.command(
            description="Lobby Owner: Remove user from the lobby",
            name='userkick'
        )
    @is_lobby_thread()
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        """Removes a user from the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                'There are no lobbies!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        if user == interaction.user:
            await interaction.response.send_message(
                'You cannot remove yourself!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        lobby_id = await self.lobby_manager.get_lobby_id_by_owner_id(
            interaction.user.id
        )
        if not lobby_id:
            await interaction.response.send_message(
                'You are not an owner of a lobby!',
                ephemeral=True
            )
            return
        # Check if user is not in the lobby
        if not await self.lobby_manager.has_joined(lobby_id, user.id):
            await interaction.response.send_message(
                f'User {user.display_name} is not in the lobby!',
                ephemeral=True
            )
            return
        # Remove user from the lobby
        try:
            await self.lobby_manager.remove_member(
                lobby_id,
                user.id,
                owner_removed=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'Error removing user {user.display_name} from the lobby: {e}',
                ephemeral=True
            )
            return
        # Send message to the user
        await interaction.response.send_message(
            f'User {user.display_name} to be removed from lobby_id {lobby_id}, \
                dispatching request to server!',
            ephemeral=True
        )
        interaction.client.dispatch("update_lobby_embed", lobby_id) # type: ignore

    @app_commands.command(
        description="Lobby Owner: Toggle ready for a user in the lobby",
        name='userready'
    )
    @is_lobby_thread()
    async def ready_user(self, interaction: discord.Interaction, user: discord.Member):
        """Toggles ready for a user in the lobby"""
        # Check if there are lobbies
        if await self.lobby_manager.get_lobbies_count() == 0:
            await interaction.response.send_message(
                'There are no lobbies!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        lobby_id = await self.lobby_manager.get_lobby_id_by_owner_id(
            interaction.user.id
        )
        if not lobby_id:
            await interaction.response.send_message(
                'You are not the owner of a lobby!',
                ephemeral=True
            )
            return
        # Check if user is in the lobby
        if not await self.lobby_manager.has_joined(lobby_id, user.id):
            await interaction.response.send_message(
                f'User {user.display_name} is not in the lobby!',
                ephemeral=True
            )
            return
        try:
            # Toggle ready for user in the lobby
            is_ready = await self.lobby_manager.set_member_state(
                lobby_id,
                user.id,
                owner_set=True
            )
        except (MemberNotFound, Exception):
            await interaction.response.send_message(
                f'User {user.display_name} not in the lobby or an error has occurred!',
                ephemeral=True
            )
            return
        # Send message to the user
        await interaction.response.send_message(
            f'User {user.display_name} is now {"ready" if is_ready else "not ready"}!',
            ephemeral=True
        )

        interaction.client.dispatch("update_lobby_embed", lobby_id) # type: ignore


async def setup(bot: commands.Bot):
    lobby_embed_manager = LobbyEmbedManager()

    lobby_manager = LobbyManager(
        repository=LobbyPostgresRepository(async_session),
        embed_manager=lobby_embed_manager,
        bot=bot
    )
    game_manager = GameManager(
        repository=GamePostgresRepository(async_session),
        embed_manager=GameEmbedManager(),
        bot=bot
    )
    # Register persistent views per lobby on restart
    lobbies: Sequence[LobbyModel] = await lobby_manager.get_all_lobbies()
    for lobby in lobbies:
        list_of_games = await game_manager.get_all_games_by_guild_id(lobby.guild_id)
        # Construct control panel - dropdown view
        bot.add_view(
            view=DropdownView(
                lobby_id=lobby.id,
                list_of_games=list_of_games,
                game_manager=game_manager,
                lobby_manager=lobby_manager,
                game_id=lobby.game_id,
                player_number=lobby.game_size,
            ),
            message_id=lobby.control_panel_message_id
        )
        # Construct button view
        bot.add_view(
            view=ButtonView(
                lobby_id=lobby.id,
                lobby_manager=lobby_manager,
                game_manager=game_manager,
            ),
            message_id=lobby.embed_message_id
        )

    await bot.add_cog(
        LobbyCog(
            bot,
            lobby_manager,
            game_manager,
        )
    )


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
