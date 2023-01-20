import asyncio
from typing import Any
from discord.ext import commands, tasks
from discord import Interaction, app_commands
import discord
from discord.ui import View, TextInput
from model.lobby_model import (
    LobbyManager,
    LobbyModel,
    LobbyState,
    MemberState,
)
from model.game_model import GameManager, GameModel
from view.lobby.embeds import LobbyEmbed, QueueEmbed, UpdateEmbedManager, UpdateEmbedType


class DropdownView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        game_manager: GameManager,
    ):
        super().__init__(timeout=None)

        # Adds the dropdown to our view object
        self.add_item(
            GameDropdown(
                lobby_id=lobby_id,
                game_manager=game_manager,
            )
        )


class GameDropdown(discord.ui.Select):
    """A select dropdown for a list of games."""

    def __init__(self, lobby_id: int, game_manager: GameManager):
        # Set the options that will be presented inside the dropdown
        self.game_manager = game_manager
        options = []
        # Create select dropdown options from file.
        for game in game_manager.load_games():
            options.append(
                discord.SelectOption(
                    label=game.game_name,
                    value=game.game_code,
                )
            )

        super().__init__(placeholder='Choose your game...',
                         min_values=1, max_values=1, options=options)
        self.lobby_id = lobby_id

    async def callback(self, interaction: discord.Interaction):

        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            # Save selected game code in state.
            LobbyManager.set_gamecode(
                interaction.client,
                self.lobby_id,
                interaction.data['values'][0] # type: ignore
            )
            # Get max number from stored [GameModel] object.
            number = self.game_manager.get_max_size(LobbyManager.get_gamecode(interaction.client, self.lobby_id))

            lobby_model = LobbyManager.get_lobby(interaction.client, self.lobby_id)

            # If the view already has a NumberDropdown for an updated one
            view: View = self.view # type: ignore
            if (len(view.children) != 1):
                view.remove_item(view.children[1])

            dropdown: GameDropdown = view.children[0] # type: ignore
            dropdown.placeholder = lobby_model.game_code
            view.add_item(
                NumberDropdown(
                    lobby_id=self.lobby_id,
                    bot=interaction.client,
                    number=number
                )
            )
            lobby_model = LobbyManager.get_lobby(
                interaction.client, self.lobby_id)
            # Send update message
            thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
            message_details = UpdateEmbedManager.get_message_details(
                bot=interaction.client,
                lobby_id=self.lobby_id,
                embed_type=UpdateEmbedType.GAME_CHANGE,
                member=interaction.user,
            )
            assert thread is not None
            await thread.send(
                content=message_details[0],
                embed=message_details[1]
            )
        # Defer interaction update
        await interaction.response.defer()
        # Edit game dropdown to reflect selected value
        await lobby_model.control_panel.edit(content="", view=self.view)


class NumberDropdown(discord.ui.Select):
    # A select dropdown for a list of numbers.
    def __init__(
        self,
        lobby_id: int,
        bot: Any,
        number: int,
    ):
        # Set the options that will be presented inside the dropdown
        options = [
            discord.SelectOption(
                label=str(x + 1)) for x in range(1, number)
        ]
        super().__init__(
            placeholder='Choose your number...',
            min_values=1,
            max_values=1,
            options=options,
        )
        self.lobby_id = lobby_id
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer()
        # Reject interaction if user is not lobby owner
        if interaction.user != LobbyManager.get_lobby_owner(self.bot, self.lobby_id):
            return

        LobbyManager.set_gamesize(
            self.bot,
            self.lobby_id,
            interaction.data['values'][0] # type: ignore
        )

        lobby_model = LobbyManager.get_lobby(self.bot, self.lobby_id)
        view: View = self.view # type: ignore

        # Set placeholder of dropdown to reflect selected value
        dropdown: NumberDropdown = view.children[1] # type: ignore
        dropdown.placeholder = interaction.data['values'][0] # type: ignore

        if lobby_model.embed_message is None:
            await lobby_model.control_panel.edit(
                content="",
                view=self.view
            )
            # Create owner embed
            embed = LobbyEmbed(
                lobby_id=self.lobby_id,
                bot=self.bot,
            )
            # Generate embed details from lobby_model
            await embed.update()
            LobbyManager.set_embed(self.bot, self.lobby_id, embed)
            # Create owner button view
            button = ButtonView(
                lobby_id=self.lobby_id,
            )
            # Send owner embed and view
            embed_message = await lobby_model.lobby_channel.send(
                embed=embed,
                view=button
            )

            LobbyManager.set_embed_message(
                self.bot, self.lobby_id, embed_message)
        else:
            self.bot.dispatch('update_lobby_embed', self.lobby_id)

        # Send update message
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        message_details = UpdateEmbedManager.get_message_details(
            bot=interaction.client,
            lobby_id=self.lobby_id,
            embed_type=UpdateEmbedType.SIZE_CHANGE,
            member=interaction.user
        )
        assert thread is not None
        await thread.send(
            content=message_details[0],
            embed=message_details[1]
        )


class DescriptionModal(discord.ui.Modal, title='Edit Description'):
    def __init__(self, lobby_id):
        super().__init__()
        self.lobby_id = lobby_id

    answer = TextInput( # type: ignore
        label='Edit Description',
        style=discord.TextStyle.paragraph,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        LobbyManager.set_descriptor(
            interaction.client, self.lobby_id, self.answer.value)
        # Send update embed
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.DESCRIPTION_CHANGE,
            interaction.user
        )
        assert thread is not None
        await thread.send(
            content=message_details[0],
            embed=message_details[1]
        )
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)


class ConfirmationModal(discord.ui.Modal, title='Are you sure? Reason optional.'):
    def __init__(self, lobby_id):
        super().__init__()
        self.lobby_id = lobby_id

    reason = TextInput( # type: ignore
        label='Reason',
        max_length=150,
        required=False
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)

        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.DELETE,
            interaction.user
        )

        embed = message_details[1]

        if self.reason.value:
            embed.add_field(
                name='Reason:',
                value=self.reason.value,
                inline=False
            )

        await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
        await channel.send(
            content=message_details[0],
            embed=embed
        )


class OwnerSelectView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int,
        list_of_users: list[tuple[str, int]]
    ):
        super().__init__()
        self.list_of_users = list_of_users
        self.add_item(
            self.OwnerDropdown(lobby_id, list_of_users)
        )

    class OwnerDropdown(discord.ui.Select):
        def __init__(
            self,
            lobby_id: int,
            list_of_users: list[tuple[str, int]]
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

        async def callback(self, interaction: discord.Interaction):
            lobby_owner = LobbyManager.get_lobby_owner(
                interaction.client, self.lobby_id)
            if interaction.user == lobby_owner:
                assert interaction.guild is not None
                member = interaction.guild.get_member(int(self.values[0]))
                assert member is not None
                LobbyManager.switch_owner(
                    interaction.client,
                    self.lobby_id,
                    member)
                LobbyManager.get_lobby_owner(interaction.client, self.lobby_id)
                interaction.client.dispatch(
                    'update_lobby_embed', self.lobby_id)
            await interaction.response.defer()
            original_channel = LobbyManager.get_original_channel(
                interaction.client, self.lobby_id)
            # Disable view after selection
            await self.view.stop() # type: ignore

            message_detail = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.OWNER_CHANGE,
                interaction.user
            )

            await original_channel.send(
                content=message_detail[0],
                embed=message_detail[1]
            )


class ButtonView(discord.ui.View):
    def __init__(
        self,
        lobby_id: int
    ):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id

    @discord.ui.button(label='Join', style=discord.ButtonStyle.green)
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button,):
        # Check if the member has already joined
        if LobbyManager.has_joined(interaction.client, self.lobby_id, interaction.user):
            await interaction.response.defer()
            return

        # Check if lobby full
        is_full = LobbyManager.is_full(interaction.client, self.lobby_id)

        # Check if lobby is locked
        lobby_state = LobbyManager.get_lobby_lock(interaction.client, self.lobby_id)

        # Check if the lobby is locked
        if lobby_state == LobbyState.LOCK or is_full:
            LobbyManager.add_member_queue(interaction.client, self.lobby_id, interaction.user)
        else:
            LobbyManager.add_member(
                interaction.client, self.lobby_id, interaction.user)

        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            UpdateEmbedType.JOIN,
            interaction.user
        )

        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)
        assert thread is not None
        await thread.send(
            content=message_details[0],
            embed=message_details[1]
        )

        # Set up queue embed if there is a queue
        channel = LobbyManager.get_channel(interaction.client, self.lobby_id)
        queue_embed_message = LobbyManager.get_queue_embed_message(
            interaction.client,
            self.lobby_id
        )
        if not queue_embed_message:
            queue_embed = QueueEmbed(interaction.client, self.lobby_id)
            queue_embed_message = await channel.send(
                embed=queue_embed
            )
            LobbyManager.set_queue_embed(interaction.client, self.lobby_id, queue_embed)
            LobbyManager.set_queue_embed_message(
                interaction.client,
                self.lobby_id,
                queue_embed_message
            )

        interaction.client.dispatch('update_lobby_embed', self.lobby_id)
        await interaction.response.defer()

    @discord.ui.button(label="Ready", style=discord.ButtonStyle.green)
    async def ready(self, interaction: discord.Interaction, button: discord.ui.Button):

        # Reject interaction if user is not in lobby
        has_joined = LobbyManager.has_joined(
            interaction.client, self.lobby_id, interaction.user)
        if not has_joined:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Reject interaction if lobby is locked
        lobby_state = LobbyManager.get_lobby_lock(
            interaction.client, self.lobby_id)
        if lobby_state == LobbyState.LOCK:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Update member state
        member_state = LobbyManager.update_member_state(
            interaction.client,
            self.lobby_id,
            interaction.user
        )

        # Update button
        number_filled = len(LobbyManager.get_members_ready(
            interaction.client, self.lobby_id))
        button.label = f"Ready: {number_filled}"
        await interaction.response.edit_message(view=self)

        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

        # Send update message
        thread = LobbyManager.get_thread(interaction.client, self.lobby_id)

        # Send update message when member readies up
        if member_state == MemberState.READY:
            message_details = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.READY,
                interaction.user
            )
            assert thread
            await thread.send(
                content=message_details[0],
                embed=message_details[1]
            )

    @discord.ui.button(label="Leave", style=discord.ButtonStyle.red)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is in lobby
        if not LobbyManager.has_joined(interaction.client, self.lobby_id, interaction.user):
            await interaction.response.defer()
            return

        embed_type = None
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        original_channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)

        # Delete lobby if there is 1 person left
        if LobbyManager.get_member_length(interaction.client, self.lobby_id) == 1:
            message_details = UpdateEmbedManager.get_message_details(
                interaction.client,
                self.lobby_id,
                UpdateEmbedType.DELETE,
                interaction.user
            )
            await original_channel.send(
                content=message_details[0],
                embed=message_details[1]
            )
            await LobbyManager.delete_lobby(interaction.client, self.lobby_id)
            return
        # Remove member from lobby
        elif interaction.user != lobby_owner:
            LobbyManager.remove_member(
                interaction.client, self.lobby_id, interaction.user)
            embed_type = UpdateEmbedType.LEAVE
        # Remove user and find new leader
        elif interaction.user == lobby_owner:
            LobbyManager.remove_owner(interaction.client, self.lobby_id)
            embed_type = UpdateEmbedType.OWNER_CHANGE

        # Move member to queue when someone leaves
        await LobbyManager.move_queue_members(interaction.client, self.lobby_id)

        # Update Ready button
        number_filled = len(LobbyManager.get_members_ready(interaction.client, self.lobby_id))
        self.ready.label = f"Ready: {number_filled}"
        await interaction.response.edit_message(view=self)
        assert embed_type
        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            embed_type,
            interaction.user
        )

        await original_channel.send(
            content=message_details[0],
            embed=message_details[1]
        )
        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)

    @discord.ui.button(label="Lock", style=discord.ButtonStyle.danger)
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):

        # Reject interaction if user is not lobby owner
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        if interaction.user != lobby_owner:
            # Defer interaction update
            await interaction.response.defer()
            return

        # Update lobby state
        lobby_status = LobbyManager.lock(interaction.client, self.lobby_id)

        status = None
        # Send update message
        if lobby_status == LobbyState.LOCK:
            button.label = "Unlock"
            status = UpdateEmbedType.LOCK
        elif lobby_status == LobbyState.UNLOCK:
            button.label = "Lock"
            status = UpdateEmbedType.UNLOCK
            await LobbyManager.move_queue_members(interaction.client, self.lobby_id)

        # Update button label
        await interaction.response.edit_message(view=self)

        # Update lobby embed
        interaction.client.dispatch('update_lobby_embed', self.lobby_id)
        # Send update message
        original_channel = LobbyManager.get_original_channel(
            interaction.client, self.lobby_id)
        assert status
        message_details = UpdateEmbedManager.get_message_details(
            interaction.client,
            self.lobby_id,
            status,
            interaction.user
        )
        await original_channel.send(
            content=message_details[0],
            embed=message_details[1]
        )

    @discord.ui.button(label="Change Leader", style=discord.ButtonStyle.blurple)
    async def change_leader(self, interaction: discord.Interaction, button: discord.ui.Button):
        lobby_owner = LobbyManager.get_lobby_owner(
            interaction.client, self.lobby_id)
        if interaction.user != lobby_owner:
            await interaction.response.defer()
        else:
            options = []
            list_of_users = LobbyManager.get_members(
                interaction.client, self.lobby_id)
            # Get a list of users
            for member_model in list_of_users:
                options.append(
                    (member_model.member.display_name, member_model.member.id))
            await interaction.response.send_message(
                view=OwnerSelectView(
                    self.lobby_id,
                    options
                ),
                ephemeral=True,
            )

    @discord.ui.button(label="Edit Descr.", style=discord.ButtonStyle.blurple)
    async def edit_description(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.defer()
        else:
            await interaction.response.send_modal(
                DescriptionModal(self.lobby_id),
            )

    @discord.ui.button(label="Disband", style=discord.ButtonStyle.blurple)
    async def disband(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user == LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            await interaction.response.send_modal(
                ConfirmationModal(self.lobby_id)
            )
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Promote", style=discord.ButtonStyle.blurple)
    async def promote(self, interaction: discord.Interaction, button: discord.ui.Button):

        class PromotionEmbed(discord.Embed):
            def __init__(self, game_model: GameModel, lobby_id: int):
                super().__init__(
                    title=f'Sponsor Friendly Ad for {game_model.game_name}',
                    color=discord.Color.dark_orange(),
                )
                channel = LobbyManager.get_channel(interaction.client, lobby_id)
                self.description = f'Click on lobby <#{channel.id}> to join!'
                lobby_size = LobbyManager.get_member_length(interaction.client, lobby_id)
                game_size = int(LobbyManager.get_gamesize(interaction.client, lobby_id))
                self.add_field(
                    name='Slots Left:',
                    value=f'R>{game_size - lobby_size}',
                )
                if game_model.icon_url:
                    self.set_thumbnail(url=game_model.icon_url)

        await interaction.response.defer()
        # If user is not lobby owner, defer interaction
        if interaction.user != LobbyManager.get_lobby_owner(interaction.client, self.lobby_id):
            return
        # If last promotion was older than 10 minutes, defer interaction
        if not LobbyManager.can_promote(interaction.client, self.lobby_id):
            return

        is_full = LobbyManager.is_full(interaction.client, self.lobby_id)
        game_manager = GameManager()
        game_model: GameModel = game_manager.get_game(
            LobbyManager.get_gamecode(interaction.client, self.lobby_id)
        )
        # If the lobby is not full, promote
        if not is_full:
            original_channel = LobbyManager.get_original_channel(
                interaction.client,
                self.lobby_id
            )
            last_message = LobbyManager.get_last_promotion_message(
                interaction.client, self.lobby_id
            )
            # If there was an older promotion, delete it
            if last_message:
                await last_message.delete()
            message = await original_channel.send(
                content=f'<@&{game_model.role}>',
                embed=PromotionEmbed(game_model=game_model, lobby_id=self.lobby_id)
            )
            LobbyManager.set_last_promotion_message(interaction.client, self.lobby_id, message)


class LobbyCog(commands.Cog):
    def __init__(self, bot: Any):

        self.bot = bot
        self.game_manager = GameManager()
        print('LobbyCog loaded')

    # Custom listeners for tasks
    # 1. Listener to update the lobby embed
    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""
        embed = LobbyManager.get_embed(self.bot, lobby_id)

        assert embed
        await embed.update()

        queue_embed = LobbyManager.get_queue_embed(self.bot, lobby_id)
        if queue_embed:
            await queue_embed.update()

    @update_lobby_embed.before_loop
    async def before_update_lobby_embed(self):
        # Add a delay to bulk edit, rate limit to update embed is 5 per 5 seconds
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(self, interaction: Interaction):
        """Creates a lobby through UI command"""

        assert interaction.guild is not None

        exist = discord.utils.get(interaction.guild.channels, name='Lobbies')

        if not exist:
            print('Lobby Category Channel does not exist, creating one...')
            exist = await interaction.guild.create_category_channel('Lobbies')

        # Check if user has created a lobby previously.
        if interaction.user.id in self.bot.lobby.keys():
            await interaction.response.send_message(
                'You have already created a lobby!',
                ephemeral=True
            )
            return

        assert isinstance(exist, discord.CategoryChannel)

        # Create new text channel
        channel = await interaction.guild.create_text_channel(
            name=f'{LobbyManager.get_lobby_name(self.bot)}',
            category=exist
        )

        # Create embed to redirect user to the new lobby channel
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f'{interaction.user.name} created a lobby ✨',
                description=f'Click <#{channel.id}> to join the lobby',
                color=discord.Color.green(),
            )
        )

        control_panel = await channel.send('Initialising lobby...')

        # Create a new lobby model
        lobby_model = LobbyModel(
            control_panel=control_panel,
            owner=interaction.user, # type: ignore
            original_channel=interaction.channel, # type: ignore
            lobby_channel=channel
        )
        LobbyManager.set_lobby(self.bot, interaction.user.id, lobby_model)
        # Create thread for logging
        thread_message = await channel.send("Creating thread...")
        thread = await channel.create_thread(
            name="History Log Thread",
            message=thread_message
        )
        LobbyManager.set_thread(self.bot, interaction.user.id, thread)
        # Add owner to the lobby
        LobbyManager.add_member(interaction.client, interaction.user.id, interaction.user), # type: ignore
        # Create a custom view to hold logic, user id is used to have one instance per user
        view = DropdownView(lobby_id=interaction.user.id, game_manager=self.game_manager)
        # Message select dropdowns in the channel
        await control_panel.edit(view=view)

    @app_commands.command(description="Add game to the lobby module", name='addgame')
    async def add_game(
        self,
        interaction: Interaction,
        game_name: str,
        game_code: str,
        role: discord.Role,
        max_size: int,
        icon_url: str | None
    ):
        """Adds a game to the lobby module"""
        # Check if the game already exists
        for game in self.game_manager.load_games():
            if game_code == game.game_code:
                await interaction.response.send_message(
                    'The game already exists!',
                    ephemeral=True
                )
                return

        # Add the game to the list
        self.game_manager.add_game(
            game_code=game_code,
            game_name=game_name,
            max_size=max_size,
            role=role.id,
            icon_url=icon_url.strip() if icon_url else None # type: ignore
        )

        # Send message to the user
        await interaction.response.send_message(
            f'Game {game_name} added!',
            ephemeral=True
        )

    @app_commands.command(description="Remove game from the lobby module", name='removegame')
    async def remove_game(
        self,
        interaction: Interaction,
        game_code: str
    ):
        """Removes a game from the lobby module"""
        # Check if the game exists
        for game in self.game_manager.load_games():
            if game_code == game.game_code:
                self.game_manager.remove_game(game_code)
                await interaction.response.send_message(
                    f'Game {game.game_name} removed!',
                    ephemeral=True
                )
                return

        # Send message to the user
        await interaction.response.send_message(
            'The game does not exist!',
            ephemeral=True
        )

    @app_commands.command(description="List all games", name='listgames')
    async def list_games(
        self,
        interaction: Interaction
    ):
        """Lists all games"""
        # Check if the game exists
        games = self.game_manager.load_games()
        if not games:
            await interaction.response.send_message(
                'There are no games!',
                ephemeral=True
            )
            return
        # Get all games
        list_of_games = '\n'.join(
            [f'Name: {game.game_name} - Code: {game.game_code}' for game in games]
        )
        # Send message to the user
        await interaction.response.send_message(
            embed=discord.Embed(
                title='Games',
                description=list_of_games,
                color=discord.Color.green(),
            ),
            ephemeral=True
        )

    @app_commands.command(description="Lobby Owner: Add user to the lobby", name='adduser')
    async def add_user(self, interaction: discord.Interaction, user: discord.Member):
        """Adds a user to the lobby"""
        # Check if there are lobbies
        if len(self.bot.lobby) == 0:
            await interaction.response.send_message(
                'There are no lobbies!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        for key, lobby_model in self.bot.lobby.items():
            if lobby_model.owner == interaction.user:
                # Add user to the lobby
                success = LobbyManager.add_member(interaction.client, key, user) # type: ignore
                # Send message to the user
                if success:
                    await interaction.response.send_message(
                        f'User {user.display_name} added!',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'User {user.display_name} already in the lobby!',
                        ephemeral=True
                    )
                interaction.client.dispatch("update_lobby_embed", key)
                return
        else:
            # Send message to the user
            await interaction.response.send_message(
                'You are not the owner of the lobby!',
                ephemeral=True
            )

    @app_commands.command(description="Lobby Owner: Remove user from the lobby", name='removeuser')
    async def remove_user(self, interaction: discord.Interaction, user: discord.Member):
        """Removes a user from the lobby"""
        # Check if there are lobbies
        if len(self.bot.lobby) == 0:
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
        for key, lobby_model in self.bot.lobby.items():
            if lobby_model.owner == interaction.user:
                # Remove user from the lobby
                success = LobbyManager.remove_member(interaction.client, key, user)  # type: ignore
                # Send message to the user
                if success:
                    await interaction.response.send_message(
                        f'User {user.display_name} removed!',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'User {user.display_name} not in the lobby!',
                        ephemeral=True
                    )
                interaction.client.dispatch("update_lobby_embed", key)
                return
        else:
            # Send message to the user
            await interaction.response.send_message(
                'You are not the owner of the lobby!',
                ephemeral=True
            )

    @app_commands.command(
        description="Lobby Owner: Toggle ready for a user in the lobby",
        name='readyuser'
    )
    async def ready_user(self, interaction: discord.Interaction, user: discord.Member):
        """Toggles ready for a user in the lobby"""
        # Check if there are lobbies
        if len(self.bot.lobby) == 0:
            await interaction.response.send_message(
                'There are no lobbies!',
                ephemeral=True
            )
            return
        # Check if interaction user is the owner of the lobby
        for key, lobby_model in self.bot.lobby.items():
            if lobby_model.owner == interaction.user:
                # Toggle ready for user in the lobby
                success = LobbyManager.update_member_state(interaction.client, key, user) # type: ignore
                # Send message to the user
                if success:
                    await interaction.response.send_message(
                        f'User {user.display_name} is now {success.value[0]}!',
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        f'User {user.display_name} not in the lobby!',
                        ephemeral=True
                    )
                interaction.client.dispatch("update_lobby_embed", key)
                return
        else:
            # Send message to the user
            await interaction.response.send_message(
                'You are not the owner of the lobby!',
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(LobbyCog(bot))


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
