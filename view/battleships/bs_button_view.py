from typing import Optional, cast, Any

from discord import ButtonStyle, Message, User, Interaction
from discord.ui import View, Button

from stubs.battleship_types import Client
from model.battleships.battleships_model import BattleShipGameManager, BattleShipGameStatus


class BattleshipSetupGridView(View):
    def __init__(self, lobby_id: int, bot: Client, user: User):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.bot = bot
        self.x = ['A', 'B', 'C', 'D', 'E']
        self.y = [1, 2, 3, 4, 5]
        self.user = user
        for x_count, letter in enumerate(self.x):
            for y_count, number in enumerate(self.y):
                self.add_item(
                    BattleShipSetupButton(
                        label=f'{letter}{number}',
                        co_ord=(x_count, y_count),
                        user=self.user,
                        bot=self.bot,
                        lobby_id=lobby_id
                    )
                )

    async def update(self) -> None:
        for grid_button in self.children:
            grid_button = cast(BattleShipSetupButton, grid_button)
            grid_button.update()
        player_view_message = BattleShipGameManager.get_player_setup_message(
            self.bot,
            self.lobby_id,
            self.user
        )
        await player_view_message.edit(view=self)

        done_button = BattleShipGameManager.get_player_done_button(
            self.bot,
            self.lobby_id,
            self.user
        )
        if done_button is not None:
            await done_button.update()

        is_done = BattleShipGameManager.get_player_grid(
            self.bot,
            self.lobby_id,
            self.user
        ).status == BattleShipGameStatus.SETUP_DONE

        if done_button is None and is_done:
            done_button = DoneButton(
                self.lobby_id,
                self.user,
                self.bot
            )
            done_view = View().add_item(
                done_button
            )
            if self.user.dm_channel is None:
                dm_channel = await self.user.create_dm()
            else:
                dm_channel = self.user.dm_channel
            message = await dm_channel.send(
                view=done_view
            )
            done_button.add_message(message)
            BattleShipGameManager.set_player_done_button(
                self.bot,
                self.lobby_id,
                self.user,
                done_button
            )


class BattleShipSetupButton(Button[Any]):
    def __init__(
            self,
            label: str,
            co_ord: tuple[int, int],
            user: User,
            bot: Client,
            lobby_id: int
    ):
        super().__init__(label=label)
        self.co_ord = co_ord
        self.style = ButtonStyle.secondary
        self.user = user
        self.bot = bot
        self.lobby_id = lobby_id

    def update(self) -> None:
        self.style = BattleShipGameManager.get_cell_status(
            self.bot,
            self.lobby_id,
            self.co_ord,
            self.user
        ).value

    async def callback(self, interaction: Interaction) -> None:
        view = BattleShipGameManager.get_player_setup_view(self.bot, self.lobby_id, self.user)
        BattleShipGameManager.add_ship(
            self.bot,
            self.lobby_id,
            self.co_ord,
            self.user
        )
        # Update the board
        await view.update()
        await interaction.response.defer()


class DoneButton(Button[Any]):
    def __init__(self, lobby_id: int, user: User, bot: Client):
        super().__init__(label='Done', style=ButtonStyle.success)
        self.lobby_id = lobby_id
        self.user = user
        self.bot = bot
        self.message: Optional[Message] = None

    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.defer()
        # Stop taking inputs from the setup view and button.
        BattleShipGameManager.get_player_setup_view(self.bot, self.lobby_id, self.user).stop()
        # Change button style and disable it.
        self.disabled = True
        self.style = ButtonStyle.danger
        # Update button
        if self.message:
            await self.message.edit(view=self.view)
        # Set setup flag to be done
        BattleShipGameManager.set_setup_done(self.bot, self.lobby_id, interaction.user)
        # Create status view on the original channel
        view = BattleShipStatusView(self.lobby_id, self.bot, self.user)
        BattleShipGameManager.set_player_status_view(self.bot, self.lobby_id, interaction.user, view)
        # Replace status placeholder with the status view
        status_message = BattleShipGameManager.get_player_status_message(self.bot, self.lobby_id, interaction.user)
        await status_message.edit(view=view)
        # Start the game
        await BattleShipGameManager.start(self.bot, self.lobby_id)

    async def update(self) -> None:
        self.disabled = BattleShipGameManager.get_player_grid(
            self.bot,
            self.lobby_id,
            self.user
        ).status != BattleShipGameStatus.SETUP_DONE
        if self.message:
            await self.message.edit(view=self.view)

    def add_message(self, message: Message) -> None:
        self.message = message


class BattleShipGameGridView(View):
    def __init__(
            self,
            lobby_id: int,
            bot: Client,
            user: User
    ):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.bot = bot
        self.user = user
        self.x = ['A', 'B', 'C', 'D', 'E']
        self.y = [1, 2, 3, 4, 5]
        for x_count, letter in enumerate(self.x):
            for y_count, number in enumerate(self.y):
                self.add_item(
                    BattleShipGameButton(
                        label=f'{letter}{number}',
                        co_ord=(x_count, y_count),
                        lobby_id=lobby_id,
                        user=self.user
                    )
                )

    def set_loser_board(self) -> None:
        """Set ships that were not hit to be red"""
        ship_co_ord = BattleShipGameManager.get_loser_ship_co_ords(self.bot, self.lobby_id)
        for button in self.children:
            casted_button = cast(Any, button)
            if casted_button.co_ord in ship_co_ord:
                if casted_button.style == ButtonStyle.secondary:
                    casted_button.style = ButtonStyle.danger

    def enable(self) -> None:
        """Enable buttons when it's the user's turn"""
        for button in self.children:
            button.disabled = False

    def disable(self) -> None:
        """Disable buttons when it's not the user's turn"""
        for button in self.children:
            button.disabled = True


class BattleShipGameButton(Button[Any]):
    def __init__(self, label: str, co_ord: tuple[int, int], lobby_id: int, user: User):
        super().__init__(label=label, style=ButtonStyle.secondary)
        self.co_ord = co_ord
        self.lobby_id = lobby_id
        self.user = user
        self.disabled = True

    async def callback(self, interaction: Interaction) -> None:
        user = BattleShipGameManager.get_turn(interaction.client, self.lobby_id)
        # If it's not the users button, return
        if self.user.id != interaction.user.id:
            await interaction.response.defer()
            return
        # If it's not the user's turn, return
        if user.id != interaction.user.id:
            await interaction.response.defer()
            return
        # If the button has been pressed before, return
        if self.style == ButtonStyle.green or self.style == ButtonStyle.blurple:
            await interaction.response.defer()
            return
        # Get miss or hit on press
        result = BattleShipGameManager.get_opponent_grid(
            interaction.client,
            self.lobby_id,
            interaction.user
        ).get_hit(self.co_ord)
        # Change the color if its hit or miss
        if result:
            self.style = ButtonStyle.success
        else:
            self.style = ButtonStyle.primary
        await BattleShipGameManager.set_turn(interaction.client, self.lobby_id)
        game_model = BattleShipGameManager.get_game(interaction.client, self.lobby_id)
        if game_model.turn.id == game_model.player_one.id:
            game_model.player_one_game_view.enable()
            game_model.player_two_game_view.disable()
        else:
            game_model.player_two_game_view.enable()
            game_model.player_one_game_view.disable()
        # Update the board
        # Disable current player's grid view
        await BattleShipGameManager.get_player_view_message(
            interaction.client,
            self.lobby_id,
            self.user
        ).edit(
            view=self.view
        )
        # Enable next player's grid view
        await BattleShipGameManager.get_player_view_message(
            interaction.client,
            self.lobby_id,
            game_model.turn
        ).edit(
            view=cast(
                View,
                BattleShipGameManager.get_player_game_view(
                    interaction.client,
                    self.lobby_id,
                    game_model.turn
                )
            )
        )
        # Update both player's status views
        await BattleShipGameManager.update_status_message(interaction.client, self.lobby_id)
        # If the game is over, stop all views
        if BattleShipGameManager.is_game_over(interaction.client, self.lobby_id):
            await BattleShipGameManager.game_over(interaction.client, self.lobby_id)
        await interaction.response.defer()


class BattleShipStatusView(View):
    def __init__(self, lobby_id: int, bot: Client, user: User):
        super().__init__(timeout=None)
        self.lobby_id = lobby_id
        self.bot = bot
        self.user = user
        self.update()

    def update(self) -> None:

        # Internal class that doesn't do anything on press
        class StatusButton(Button[Any]):
            def __init__(self, label: str, style: ButtonStyle):
                super().__init__(label=label, style=style)

            async def callback(self, interaction: Interaction) -> None:
                await interaction.response.defer()

        # Start update by clearing the view.
        self.clear_items()

        # If the game is over, add button that shows player's outcome
        if BattleShipGameManager.is_game_over(self.bot, self.lobby_id):
            winner_id = BattleShipGameManager.get_winner(self.bot, self.lobby_id)
            if winner_id == self.user.id:
                self.add_item(
                    Button(
                        label=f"{self.user.display_name} wins!",
                        style=ButtonStyle.success
                    )
                )
            else:
                self.add_item(
                    Button(
                        label=f"{self.user.display_name} loses!",
                        style=ButtonStyle.danger
                    )
                )
            return

        hit_status = BattleShipGameManager.get_status_hits(self.bot, self.lobby_id, self.user)
        turn = BattleShipGameManager.get_turn(self.bot, self.lobby_id)

        if turn:
            if turn.id == self.user.id:
                button_style = ButtonStyle.success
            else:
                button_style = ButtonStyle.secondary
        else:
            button_style = ButtonStyle.secondary

        self.add_item(
            StatusButton(
                label=f"Player: {self.user.display_name}",
                style=button_style
            )
        )
        self.add_item(
            StatusButton(
                label=f"Hits: {hit_status}/10",
                style=button_style
            )
        )
