import asyncio
from discord.ext import commands, tasks  # type: ignore
from discord.ext.commands import Bot, Cog
from discord import Interaction, app_commands, TextChannel
import discord
from typing import cast

from stubs.lobby_types import Client
from view.lobby.dropdown import DropdownView
from model.lobby.lobby_model import (
    LobbyManager,
    LobbyModel,
)
from model.lobby.game_model import GameManager


class LobbyCog(Cog):  # type: ignore
    def __init__(self, bot: Client):
        self.bot = bot

        self.game_manager = GameManager()
        print('LobbyCog loaded')

    # Custom listeners for tasks
    # 1. Listener to update the lobby embed
    @tasks.loop(count=1, reconnect=True)  # type: ignore
    async def update_lobby_embed(self, lobby_id: int) -> None:
        """Updates the embed of the lobby message"""
        embed = LobbyManager.get_embed(self.bot, lobby_id)
        if embed is not None:
            await embed.update()  # type: ignore

    @update_lobby_embed.before_loop  # type: ignore
    async def before_update_lobby_embed(self) -> None:
        # Add a delay to bulk edit, rate limit to update embed is 5 per 5 seconds
        await asyncio.sleep(5)

    @commands.Cog.listener()  # type: ignore
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(self, interaction: Interaction) -> None:
        """Creates a lobby through UI command"""
        if not interaction.guild:
            raise Exception('Interaction does not have a guild')
        exist = discord.utils.get(interaction.guild.categories, name='Lobbies')

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

        # Create new text channel
        channel = await interaction.guild.create_text_channel(
            name=f'{LobbyManager.get_lobby_name(interaction.client)}',
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
            owner=interaction.user,
            original_channel=cast(TextChannel, interaction.channel),
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
        LobbyManager.add_member(interaction.client, interaction.user.id, interaction.user),
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
    ) -> None:
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
            icon_url=icon_url.strip() if icon_url else None
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
    ) -> None:
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
    ) -> None:
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

    @app_commands.command(description="Add user to the lobby", name='adduser')
    async def add_user(self, interaction: discord.Interaction, user: discord.User) -> None:
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
                success = LobbyManager.add_member(interaction.client, key, user)
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

    @app_commands.command(description="Remove user from the lobby", name='removeuser')
    async def remove_user(self, interaction: discord.Interaction, user: discord.User) -> None:
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
                success = LobbyManager.remove_member(interaction.client, key, user)
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


async def setup(bot: Bot) -> None:
    await bot.add_cog(LobbyCog(cast(Client, bot)))


async def teardown(bot: Bot) -> None:
    await bot.remove_cog(LobbyCog(cast(Client, bot)).qualified_name)
