from typing import cast

from discord import Interaction, app_commands, User, TextChannel
from discord.ext.commands import Bot, Cog

from stubs.battleship_types import Channel, Client
from model.battleships.battleships_model import (
    BattleShipGameManager,
    BattleShipGameModel,
    BattleShipGrid
)
from view.battleships.bs_button_view import BattleshipSetupGridView, BattleShipGameGridView


class BattleshipCog(Cog):  # type: ignore
    def __init__(self, bot: Client):
        self.bot = bot
        self.bot.battleship_games = {}
        print('BattleshipCog loaded')

    @app_commands.command(description="Start a new game of battleship", name='battleship')
    async def battleship(self, interaction: Interaction, user: User) -> None:
        await interaction.response.send_message(
            content="Sending setup boards to players...",
            ephemeral=True
        )
        # Create setup view for player 1
        view1 = BattleshipSetupGridView(
            lobby_id=interaction.user.id,
            bot=interaction.client,
            user=interaction.user
        )
        # Create setup view for player 2
        view2 = BattleshipSetupGridView(
            lobby_id=interaction.user.id,
            bot=interaction.client,
            user=user
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
        # Initialise game grid view for player 1
        player_one_game_view = BattleShipGameGridView(interaction.user.id, interaction.client, interaction.user)
        # Initialise game grid view for player 2
        player_two_game_view = BattleShipGameGridView(interaction.user.id, interaction.client, user)
        if isinstance(interaction.channel, TextChannel):
            channel: Channel = interaction.channel
        else:
            raise ValueError("Channel should be TextChannel")
        # Send status message for player 1
        player_one_status_message = await channel.send(
            content="Waiting for player one to setup board."
        )
        # Send game grid for player 1
        player_one_game_message = await interaction.channel.send(
            view=player_one_game_view
        )
        # Send status message for player 2
        player_two_status_message = await interaction.channel.send(
            content="Waiting for player two to setup board."
        )
        # Send game grid for player 2
        player_two_game_message = await interaction.channel.send(
            view=player_two_game_view
        )
        # Initialise battleship game model
        game_model = BattleShipGameModel(
            original_channel=interaction.channel,
            player_one=interaction.user,
            player_one_setup_view=view1,
            player_one_grid=BattleShipGrid(),
            player_one_setup_message=player_one_message,
            player_one_game_view=player_one_game_view,
            player_one_game_message=player_one_game_message,
            player_one_status_message=player_one_status_message,
            player_two=user,
            player_two_setup_view=view2,
            player_two_grid=BattleShipGrid(),
            player_two_setup_message=player_two_message,
            player_two_game_view=player_two_game_view,
            player_two_game_message=player_two_game_message,
            player_two_status_message=player_two_status_message,
            turn=interaction.user
        )
        # Attach game model to bot
        BattleShipGameManager.set_game(interaction.client, interaction.user.id, game_model)


async def setup(bot: Bot) -> None:
    await bot.add_cog(BattleshipCog(cast(Client, bot)))


async def teardown(bot: Bot) -> None:
    await bot.remove_cog(BattleshipCog(cast(Client, bot)).qualified_name)
