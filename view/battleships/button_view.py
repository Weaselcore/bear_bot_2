from discord.ui import View, Button
from discord import Interaction, ButtonStyle, Member
from discord.ext import commands

from model.battleships.battleships_model import BattleShipGameManager, BattleShipGameStatus


class BattleshipSetUpGridView(View):
    def __init__(self, battleship_game_id: int, bot: commands.Bot, member: Member):
        super().__init__(timeout=None)
        self.battleship_game_id = battleship_game_id
        self.bot = bot
        self.x = ['A', 'B', 'C', 'D', 'E']
        self.y = [1, 2, 3, 4, 5]
        self.member = member
        for x_count, letter in enumerate(self.x):
            for y_count, number in enumerate(self.y):
                self.add_item(
                    BattleShipSetupButton(
                        label=f'{letter}{number}',
                        co_ord=(x_count, y_count),
                        member=self.member
                    )
                )

    async def update(self):
        for grid_button in self.children:
            grid_button.update()
        player_view_message = BattleShipGameManager.get_player_view_message(
            self.bot,
            self.battleship_game_id,
            self.member
        )
        await player_view_message.edit(view=self)

        done_button = BattleShipGameManager.get_player_done_button(
            self.bot,
            self.battleship_game_id,
            self.member
        )
        if done_button is not None:
            await done_button.update()

        is_done = BattleShipGameManager.get_player_grid(
            self.bot,
            self.battleship_game_id,
            self.member
        ).status == BattleShipGameStatus.SETUP_DONE

        if done_button is None and is_done:
            done_button = DoneButton(
                lobby_id=self.battleship_game_id,
                member=self.member,
                bot=self.bot
            )
            done_view = View().add_item(
                done_button
            )
            message = await self.member.dm_channel.send(
                view=done_view
            )
            done_button.add_message(message)
            BattleShipGameManager.set_player_done_button(
                self.bot,
                self.battleship_game_id,
                self.member,
                done_button
            )


class BattleShipSetupButton(Button):
    def __init__(self, label: str, co_ord: tuple[int, int], member: Member):
        super().__init__(label=label)
        self.co_ord = co_ord
        self.style = ButtonStyle.secondary
        self.member = member

    def update(self):
        self.style = BattleShipGameManager.get_cell_status(
            self.view.bot,
            self.view.battleship_game_id,
            self.co_ord,
            self.member
        ).value

    async def callback(self, interaction: Interaction):
        BattleShipGameManager.add_ship(
            interaction.client,
            self.view.battleship_game_id,
            self.co_ord,
            self.member
        )
        # Update the board
        await self.view.update()
        await interaction.response.defer()


class DoneButton(Button):
    def __init__(self, lobby_id: int, member: Member, bot: commands.Bot):
        super().__init__(label='Done', style=ButtonStyle.success)
        self.lobby_id = lobby_id
        self.member = member
        self.bot = bot
        self.message = None

    async def callback(self, interaction: Interaction):
        await interaction.response.defer()
        BattleShipGameManager.get_player_setup_view(self.bot, self.lobby_id, self.member).stop()
        self.color = ButtonStyle.red
        self.disabled = True
        await self.message.edit(view=self.view)
        BattleShipGameManager.set_setup_done(self.bot, self.lobby_id, interaction.user)
        original_channel = BattleShipGameManager.get_original_channel(self.bot, self.lobby_id)
        if BattleShipGameManager.get_game_status_message(self.bot, self.lobby_id) is None:
            view = BattleShipStatusView(self.lobby_id, self.bot)
            game_status_message = await original_channel.send(
                view=view
            )
            BattleShipGameManager.set_game_status_view(self.bot, self.lobby_id, view)
            BattleShipGameManager.set_game_status_message(self.bot, self.lobby_id, game_status_message) #noqa
        if BattleShipGameManager.get_game_message(self.bot, self.lobby_id) is None:
            game_message = await original_channel.send(
                "Initialising game..."
            )
            BattleShipGameManager.set_game_message(self.bot, self.lobby_id, game_message)
        if BattleShipGameManager.get_setup_done(self.bot, self.lobby_id):
            await BattleShipGameManager.start(
                self.bot,
                self.lobby_id,
                BattleShipGameManager.get_game_status_message(self.bot, self.lobby_id),
                BattleShipGameManager.get_game_message(self.bot, self.lobby_id),
                BattleShipGameGridView(self.lobby_id, self.bot),
                BattleShipGameGridView(self.lobby_id, self.bot)
            )

    async def update(self):
        self.disabled = BattleShipGameManager.get_player_grid(
            self.bot,
            self.lobby_id,
            self.member
        ).status != BattleShipGameStatus.SETUP_DONE
        await self.message.edit(view=self.view)

    def add_message(self, message):
        self.message = message


class BattleShipGameGridView(View):
    def __init__(
        self,
        battleship_game_id: int,
        bot: commands.Bot,
    ):
        super().__init__(timeout=None)
        self.battleship_game_id = battleship_game_id
        self.bot = bot
        self.x = ['A', 'B', 'C', 'D', 'E']
        self.y = [1, 2, 3, 4, 5]
        for x_count, letter in enumerate(self.x):
            for y_count, number in enumerate(self.y):
                self.add_item(
                    BattleShipGameButton(
                        label=f'{letter}{number}',
                        co_ord=(x_count, y_count),
                    )
                )

    async def update(self):
        member = BattleShipGameManager.get_turn(self.bot, self.battleship_game_id)
        await BattleShipGameManager.update_game_message(self.bot, self.battleship_game_id)
        BattleShipGameManager.set_player_game_view(
            self.bot,
            self.battleship_game_id,
            member,
            self
        )
        BattleShipGameManager.set_turn(self.bot, self.battleship_game_id)
        self.bot.dispatch("update_battleship_grid", self.battleship_game_id)


class BattleShipGameButton(Button):
    def __init__(self, label: str, co_ord: tuple[int, int]):
        super().__init__(label=label)
        self.co_ord = co_ord
        self.style = ButtonStyle.secondary

    async def callback(self, interaction: Interaction):
        member = BattleShipGameManager.get_turn(interaction.client, self.view.battleship_game_id)
        # If its not the members turn, return
        if member != interaction.user:
            await interaction.response.defer()
            return
        # If the button has been pressed before, return
        if self.style == ButtonStyle.red or self.style == ButtonStyle.blurple:
            await interaction.response.defer()
            return
        # If game state is locked; when grid is being refreshed, return
        if BattleShipGameManager.get_lock(interaction.client, self.view.battleship_game_id):
            await interaction.response.defer()
            return
        # Get miss or hit on press
        result = BattleShipGameManager.get_opponent_grid(
            interaction.client,
            self.view.battleship_game_id,
            interaction.user
        ).get_hit(self.co_ord)
        # Change the color if its hit or miss
        if result:
            self.style = ButtonStyle.red
        else:
            self.style = ButtonStyle.blurple
        # Update the board
        await self.view.update()
        BattleShipGameManager.set_lock(interaction.client, self.view.battleship_game_id)
        await interaction.response.defer()


class BattleShipStatusView(View):
    def __init__(self, battleship_game_id: int, bot: commands.Bot):
        super().__init__(timeout=None)
        self.battleship_game_id = battleship_game_id
        self.bot = bot
        self.update()

    def update(self):

        class StatusButton(Button):
            def __init__(self, label: str, style: ButtonStyle):
                super().__init__(label=label, style=style)

            async def callback(self, interaction: Interaction, _):
                await interaction.response.defer()

        self.clear_items()
        if BattleShipGameManager.is_game_over(self.bot, self.battleship_game_id):
            winner_name = BattleShipGameManager.game_over(self.bot, self.battleship_game_id)
            self.add_item(
                Button(
                    label=f"{winner_name} wins!",
                    style=ButtonStyle.green
                )
            )
            return
        data_tuple = BattleShipGameManager.get_status(self.bot, self.battleship_game_id)
        player_1_button_style = None
        player_2_button_style = None
        turn = BattleShipGameManager.get_turn(self.bot, self.battleship_game_id)

        if turn.display_name == data_tuple[0]:
            player_1_button_style = ButtonStyle.green
            player_2_button_style = ButtonStyle.gray
        else:
            player_1_button_style = ButtonStyle.gray
            player_2_button_style = ButtonStyle.green

        self.add_item(
            StatusButton(
                label=f"{data_tuple[0]}",
                style=player_1_button_style
            )
        )
        self.add_item(
            StatusButton(
                label=f"Hits: {data_tuple[1]}/10",
                style=player_1_button_style
            )
        )
        self.add_item(
            StatusButton(
                label=f"{data_tuple[2]}",
                style=player_2_button_style
            )
        )
        self.add_item(
            StatusButton(
                label=f"Hits: {data_tuple[3]}/10",
                style=player_2_button_style
            )
        )
