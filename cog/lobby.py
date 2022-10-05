import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord import Interaction, app_commands
import discord

from view.lobby.dropdown import DropdownView
from view.lobby.embeds import UpdateMessageEmbed
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
            self.current_promotion: Promotion = await self.get_oldest_schedule()
            if not self.current_promotion.has_promoted:
                message = await self.current_promotion.original_channel.send(
                    content=f'<@&{self.current_promotion.game.role}>',
                    embed=PromotionEmbed(
                        bot=self.bot,
                        promotion=self.current_promotion
                    )
                )
                LobbyManager.set_last_promotion_message(
                    self.bot,
                    self.current_promotion.lobby_id,
                    message.id
                )
                self.current_promotion.has_promoted = True
            await discord.utils.sleep_until(self.current_promotion.date_time)
            if self.current_promotion in self.lobby_to_promote:
                message = await self.current_promotion.original_channel.send(
                    content=f'<@&{self.current_promotion.game.role}>',
                    embed=PromotionEmbed(
                        bot=self.bot,
                        promotion=self.current_promotion
                    )
                )
                last_message = LobbyManager.get_last_promotion_message(
                    self.bot,
                    self.current_promotion.lobby_id
                )
                if last_message:
                    last_message = await self.current_promotion.original_channel.fetch_message(
                        last_message
                    )
                    await last_message.delete()
                LobbyManager.set_last_promotion_message(
                    self.bot,
                    self.current_promotion.lobby_id,
                    message.id
                )
                # Recalculate new datetime
                self.current_promotion.update_date_time()

    async def get_oldest_schedule(self):
        if len(self.lobby_to_promote) == 0:
            await self.has_schedule.wait()
        return min(self.lobby_to_promote, key=lambda x: x.date_time)

    def schedule_item(self, item: Promotion):
        if len(self.lobby_to_promote) == 0:
            self.lobby_to_promote.append(item)
            self.has_schedule.set()
            return

        self.lobby_to_promote.append(item)

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
        await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_update_lobby_embed(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_lobby_embed.is_running():
            self.update_lobby_embed.start(lobby_id)

    @commands.Cog.listener()
    async def on_promote_lobby(self, lobby_id: int):
        """Promote the lobby"""
        print(f'Promoting lobby {lobby_id}')
        if lobby_id not in self.lobby_to_promote:
            self.schedule_item(
                item=Promotion(
                    lobby_id=lobby_id,
                    game=self.game_manager.get_game(LobbyManager.get_gamecode(self.bot, lobby_id)),
                    original_channel=LobbyManager.get_original_channel(self.bot, lobby_id)
                )
            )

    @commands.Cog.listener()
    async def on_stop_promote_lobby(self, lobby_id: int):
        """Stop promoting the lobby"""
        print(f'Stop promoting lobby {lobby_id}')
        for game_model in self.lobby_to_promote:
            if game_model.lobby_id == lobby_id:
                self.remove_schedule(game_model)

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
            name="Thread Log",
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

        # Send message to the user
        await interaction.response.send_message(
            embed=discord.Embed(
                title='Games',
                description='\n'.join([f'{game.game_name} - {game.game_code}' for game in games]),
                color=discord.Color.green(),
            ),
            ephemeral=True
        )

    # TODO: Refactor out of this class
    @commands.Cog.listener()
    async def on_owner_leave(
        self,
        lobby_id: int,
        interaction: discord.Interaction,
    ):
        lobby_owner = LobbyManager.get_lobby_owner(self.bot, lobby_id)
        if interaction.user != lobby_owner:
            await interaction.response.defer()
            return
        count = LobbyManager.get_member_length(self.bot, lobby_id)
        if count == 1:
            channel = LobbyManager.get_original_channel(self.bot, lobby_id)
            await channel.send(
                embed=UpdateMessageEmbed(
                    title="Lobby Closed",
                    value=f"🛑 Lobby {interaction.channel.name} has been deleted.",
                    color=discord.Color.red()
                )
            )
            await LobbyManager.delete_lobby(self.bot, lobby_id)
        else:
            success = await LobbyManager.remove_owner(self.bot, lobby_id)
            if success:
                LobbyManager.get_lobby_owner(self.bot, lobby_id)
        interaction.client.dispatch('update_lobby_embed', lobby_id)
        await interaction.response.defer()


async def setup(bot):
    await bot.add_cog(LobbyCog(bot))


async def teardown(bot):
    await bot.remove_cog(LobbyCog(bot))
