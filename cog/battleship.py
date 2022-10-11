import asyncio
from discord.ext import commands, tasks
from discord import Interaction, app_commands, Member
from model.battleships.battleships_model import (
    BattleShipGameManager,
    BattleShipGameModel,
    BattleShipGrid
)

from view.battleships.button_view import BattleShipStatusView, BattleshipSetUpGridView


class BattleshipCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.battleship_games = {}
        print('BattleshipCog loaded')

    @app_commands.command(description="Start a new game of battleship", name='battleship')
    async def battleship(self, interaction: Interaction, user: Member):
        # Create setup view for player 1
        view1 = BattleshipSetUpGridView(
            battleship_game_id=interaction.user.id,
            bot=interaction.client,
            member=interaction.user
        )
        # Create setup view for player 2
        view2 = BattleshipSetUpGridView(
            battleship_game_id=interaction.user.id,
            bot=interaction.client,
            member=user
        )
        # Create message for player 1
        dm_channel = interaction.user.dm_channel
        if not dm_channel:
            dm_channel = await interaction.user.create_dm()
        player_one_message = await dm_channel.send(view=view1)
        # Create message for player 2
        dm_channel = user.dm_channel
        if not dm_channel:
            dm_channel = await user.create_dm()
        player_two_message = await dm_channel.send(view=view2)
        # Initialise battleship game model
        game_model = BattleShipGameModel(
            original_channel=interaction.channel,
            player_one=interaction.user,
            player_one_setup_view=view1,
            player_one_grid=BattleShipGrid(),
            player_one_setup_message=player_one_message,
            player_two=user,
            player_two_setup_view=view2,
            player_two_grid=BattleShipGrid(),
            player_two_setup_message=player_two_message,
            turn=interaction.user
        )
        # Attach game model to bot
        BattleShipGameManager.set_game(self.bot, interaction.user.id, game_model)

        await interaction.response.send_message(
            "Sending setup boards to players...",
            ephemeral=True
        )

    @tasks.loop(count=1, reconnect=True)
    async def update_battleship_grid(self, lobby_id: int):
        """Updates the battleship grid"""
        await BattleShipGameManager.update_game_message(self.bot, lobby_id)
        await BattleShipGameManager.get_game_status_message(
            self.bot,
            lobby_id
        ).edit(
            content=None,
            view=BattleShipStatusView(lobby_id, self.bot)
        )
        BattleShipGameManager.release_lock(self.bot, lobby_id)

    @update_battleship_grid.before_loop
    async def before_update_lobby_embed(self):
        # Add a delay to bulk edit, rate limit to update embed is 5 per 5 seconds
        await asyncio.sleep(2)

    @commands.Cog.listener()
    async def on_update_battleship_grid(self, lobby_id: int):
        """Updates the lobby embed"""
        if not self.update_battleship_grid.is_running():
            self.update_battleship_grid.start(lobby_id)


async def setup(bot):
    await bot.add_cog(BattleshipCog(bot))


async def teardown(bot):
    await bot.remove_cog(BattleshipCog(bot))
