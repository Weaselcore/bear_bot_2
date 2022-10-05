import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import Interaction, app_commands
import discord

from view.lobby.dropdown import DropdownView
from model.lobby_model import (
    LobbyManager,
    LobbyModel,
)
from model.game_model import GameManager, GameModel


@dataclass
class Promotion:
    lobby_id: int
    game: GameModel
    original_channel: discord.TextChannel
    date_time = datetime.now() + timedelta(minutes=10.0)
    has_promoted = False

    def update_date_time(self):
        self.date_time = datetime.now() + timedelta(minutes=10.0)

    def __repr__(self):
        return f"Promotion: {self.lobby_id}, {self.game.game_code}, {str(self.date_time)}" \
            + f", has_promoted: {self.has_promoted}"


class PromotionEmbed(discord.Embed):
    def __init__(self, bot: commands.Bot, promotion: Promotion):
        super().__init__(
            title=f'Sponsor Friendly Ad for {promotion.game.game_name}',
            color=discord.Color.dark_orange(),
        )
        channel = LobbyManager.get_channel(bot, promotion.lobby_id)
        self.description = f'Click on lobby <#{channel.id}> to join!'
        self.set_author(name=bot.user.name, icon_url=bot.user.display_avatar.url)
        lobby_size = LobbyManager.get_member_length(bot, promotion.lobby_id)
        game_size = int(LobbyManager.get_gamesize(bot, promotion.lobby_id))
        self.add_field(
            name='Slots Left:',
            value=f'R>{game_size - lobby_size}',
        )
        if promotion.game.icon_url:
            self.set_thumbnail(url=promotion.game.icon_url)


class LobbyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Promotion scheduler variables
        self.lobby_to_promote: list[Promotion] = []
        self.task = bot.loop.create_task(self.promotion_scheduler())
        self.has_schedule = asyncio.Event()
        self.current_promotion: Promotion = None
        self.game_manager = GameManager()
        print('LobbyCog loaded')

    async def promotion_scheduler(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            # Get the next item to be scheduled
            self.current_promotion: Promotion = await self.get_oldest_schedule()
            # Promote immediately if the lobby hasn't been promoted before
            if not self.current_promotion.has_promoted:
                await self._promote()
                self.current_promotion.has_promoted = True
            # Sleep till the promotion is due to be executed
            await discord.utils.sleep_until(self.current_promotion.date_time)
            # If the item is still in the list, promote it.
            if self.current_promotion in self.lobby_to_promote:
                await self._promote()
                # Recalculate new datetime
                self.current_promotion.update_date_time()

    async def _promote(self):
        # Might not be the first time the lobby has been promoted; Delete old ad
        last_message = LobbyManager.get_last_promotion_message(
            self.bot,
            self.current_promotion.lobby_id
        )
        # Try to delete old message
        if last_message:
            try:
                await last_message.delete()
            except discord.errors.NotFound:
                pass
        # Send new ad
        message = await self.current_promotion.original_channel.send(
            content=f'<@&{self.current_promotion.game.role}>',
            embed=PromotionEmbed(
                bot=self.bot,
                promotion=self.current_promotion
            )
        )
        # Store last promotion message
        LobbyManager.set_last_promotion_message(
            self.bot,
            self.current_promotion.lobby_id,
            message
        )

    async def get_oldest_schedule(self):
        # If the list is empty, wait for an item to be added
        if len(self.lobby_to_promote) == 0:
            await self.has_schedule.wait()
        # Get the oldest item
        return min(self.lobby_to_promote, key=lambda x: x.date_time)

    def schedule_item(self, item: Promotion):
        # Add item to list and resume the scheduler
        if len(self.lobby_to_promote) == 0:
            self.lobby_to_promote.append(item)
            self.has_schedule.set()
            return
        # Add item to list if the scheduler is running
        self.lobby_to_promote.append(item)
        # If the item is the oldest, cancel the current promotion and start a new one
        if self.current_promotion is not None and item.date_time < self.current_promotion.date_time:
            self.task.cancel()
            self.task = self.bot.loop.create_task(self.promotion_scheduler())

    def remove_schedule(self, item: Promotion):
        try:
            self.lobby_to_promote.remove(item)
        except ValueError:
            pass
        else:
            if len(self.lobby_to_promote) == 0:
                self.has_schedule.clear()

    # Custom listeners for tasks
    # 1. Listener to update the lobby embed
    # 2. Listener to add and remove promotion to scheduler
    @tasks.loop(count=1, reconnect=True)
    async def update_lobby_embed(self, lobby_id: int):
        """Updates the embed of the lobby message"""
        embed = LobbyManager.get_embed(self.bot, lobby_id)
        await embed.update()

    @update_lobby_embed.before_loop
    async def before_update_lobby_embed(self):
        # Add a delay to bulk edit, rate limit to update embed is 5 per 5 seconds
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @commands.Cog.listener()
    async def on_promote_lobby(self, lobby_id: int):
        """Promote the lobby"""
        if lobby_id not in self.lobby_to_promote:
            self.schedule_item(
                item=Promotion(
                    lobby_id=lobby_id,
                    game=self.game_manager.get_game(LobbyManager.get_gamecode(self.bot, lobby_id)),
                    original_channel=LobbyManager.get_original_channel(self.bot, lobby_id)
                )
            )
            LobbyManager.set_is_promoting(self.bot, lobby_id, True)

    @commands.Cog.listener()
    async def on_stop_promote_lobby(self, lobby_id: int):
        """Stop promoting the lobby"""
        for game_model in self.lobby_to_promote:
            if game_model.lobby_id == lobby_id:
                self.remove_schedule(game_model)
                LobbyManager.set_is_promoting(self.bot, lobby_id, False)

    @app_commands.command(description="Create lobby through UI", name='lobby')
    async def create_lobby(self, interaction: Interaction):
        """Creates a lobby through UI command"""
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
            owner=interaction.user,
            original_channel=interaction.channel,
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


async def setup(bot):
    await bot.add_cog(LobbyCog(bot))


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
