from dataclasses import dataclass
from enum import Enum
from typing import cast, Any

from discord import Message, ButtonStyle, TextChannel, User
from discord.ui import View, Button

from stubs.battleship_types import (
    BattleShipGameGridView,
    DoneButton,
    BattleShipStatusView,
    BattleshipSetupGridView,
    Client
)


class BattleShipGameStatus(Enum):
    """ Status of a battleship game """
    SETUP = 0
    SETUP_DONE = 1
    FINISHED = 2


class ShipOrientation(Enum):
    """ Orientation of a ship """
    EAST = (1, 0)
    SOUTH = (0, 1)
    WEST = (-1, 0)
    NORTH = (0, -1)
    NONE = None


class BattleShipCellStatus(Enum):
    """ Status of a battleship cell """
    EMPTY = ButtonStyle.gray
    SHIP_ORIGIN = ButtonStyle.blurple
    SHIP = ButtonStyle.green
    HIT = ButtonStyle.red
    MISS = ButtonStyle.blurple


class Ship:
    """ Ship object """

    def __init__(self, length: int):
        self.length: int = length
        self.origin: tuple[int, int] | None = None
        self._xy: list[tuple[int, int]] = []
        self._orientation: list[ShipOrientation] = [
            ShipOrientation.EAST,
            ShipOrientation.SOUTH,
            ShipOrientation.WEST,
            ShipOrientation.NORTH,
            ShipOrientation.NONE
        ]
        self._current_orientation: int = 0

    def get_co_ord(self) -> list[tuple[int, int]]:
        """ Get co-ordinates of ship """
        return self._xy

    def set_co_ord(self, co_ord: list[tuple[int, int]]) -> None:
        """ Add co-ordinate to ship """
        self._xy = co_ord
        self.origin = (self._xy[0][0], self._xy[0][1])

    def rotate(self) -> ShipOrientation:
        """ Rotate ship """
        if self._current_orientation == 4:
            self._current_orientation = 0
        else:
            if self.length == 1:
                # Special case for 1x1 ships
                self._current_orientation = 4
            else:
                self._current_orientation += 1
        return self._orientation[self._current_orientation]

    def get_orientation(self) -> ShipOrientation:
        """ Get orientation of ship """
        return self._orientation[self._current_orientation]

    def get_origin(self) -> tuple[int, int] | None:
        """ Get origin of ship """
        return self.origin

    def reset(self) -> None:
        """ Reset ship """
        self._xy = []
        self.origin = None
        self._current_orientation = 0


@dataclass
class BattleShipGrid:
    """ BattleShipGrid object """

    def __init__(self) -> None:
        self.grid = [[BattleShipCellStatus.EMPTY for _ in range(5)] for _ in range(5)]
        patrol_boat = Ship(1)
        submarine = Ship(2)
        destroyer = Ship(3)
        battleship = Ship(4)
        self.ship_setup = (patrol_boat, submarine, destroyer, battleship)
        self.current_ship: Ship | None = patrol_boat
        self.status = BattleShipGameStatus.SETUP
        self.hits = 0

    def _calculate_co_ord(self, x: int, y: int, ship: Ship) -> bool:
        """ Calculate co-ordinates of ship """
        new_co_ords: list[tuple[int, int]] = []
        vector = ship.get_orientation().value
        if vector is None:
            return False
        for number in range(ship.length):
            i: int = x + (number * vector[1])
            j: int = y + (number * vector[0])
            if i < 0 or i > 4 or j < 0 or j > 4:
                return False
            result = self.grid[i][j]
            if result == BattleShipCellStatus.SHIP or result == BattleShipCellStatus.SHIP_ORIGIN:
                return False
            new_co_ords.append((i, j))
            ship.origin = (x, y)
        else:
            for count, co_ord in enumerate(new_co_ords):
                if count == 0:
                    self.grid[co_ord[0]][co_ord[1]] = BattleShipCellStatus.SHIP_ORIGIN
                else:
                    self.grid[co_ord[0]][co_ord[1]] = BattleShipCellStatus.SHIP
            ship.set_co_ord(new_co_ords)
            return True

    def get_next_ship(self) -> Ship | None:
        """ Get next ship """
        for ship in self.ship_setup:
            if len(ship.get_co_ord()) == 0:
                return ship
        return None

    def get_ship_from_origin(self, co_ord: tuple[int, int]) -> Ship | None:
        """ Get ship from origin """
        for ship in self.ship_setup:
            if ship.get_origin() == co_ord:
                return ship
        return None

    def remove_ship(self, ship: Ship) -> None:
        """ Remove ship from grid """
        for co_ord in ship.get_co_ord():
            self.grid[co_ord[0]][co_ord[1]] = BattleShipCellStatus.EMPTY

    def add_ship(self, co_ord: tuple[int, int]) -> None:
        """ Add ship to grid """
        ship = self.get_ship_from_origin(co_ord)
        # User clicks on ship origin
        if ship is not None:
            self.current_ship = ship
            self.clear_ship(self.current_ship)
            self.current_ship.rotate()
        else:
            # User clicks on empty cell
            self.current_ship = self.get_next_ship()
            # If there are no more ships to place
            if self.current_ship is None:
                self.status = BattleShipGameStatus.SETUP_DONE
                return
        success = False
        while not success:
            # Check if ship is out of bounds or overlaps with another ship
            success = self._calculate_co_ord(
                co_ord[0], co_ord[1], self.current_ship)
            if not success:
                self.clear_ship(self.current_ship)
                # Remove ship from grid
                if self.current_ship.get_orientation() == ShipOrientation.NONE:
                    self.clear_ship(self.current_ship)
                    self.current_ship.reset()
                    break
                # Check next orientation if valid
                self.current_ship.rotate()
        # After placing ship, set grid status
        if self.get_next_ship() is None:
            self.status = BattleShipGameStatus.SETUP_DONE
        else:
            self.status = BattleShipGameStatus.SETUP

    def clear_ship(self, ship: Ship) -> None:
        """ Clear ship """
        ship_co_ord = ship.get_co_ord()
        if len(ship_co_ord) != 0:
            for cell in range(ship.length - 1, -1, -1):
                self.grid[ship_co_ord[cell][0]][ship_co_ord[cell][1]] = BattleShipCellStatus.EMPTY

    def get_cell_status(self, co_ord: tuple[int, int]) -> BattleShipCellStatus:
        """ Get cell status """
        return self.grid[co_ord[0]][co_ord[1]]

    def get_hit(self, co_ord: tuple[int, int]) -> bool:
        """ Get hit """
        cell = self.grid[co_ord[0]][co_ord[1]]
        if cell == BattleShipCellStatus.SHIP or cell == BattleShipCellStatus.SHIP_ORIGIN:
            self.hits += 1
            return True
        else:
            return False

    def game_over(self) -> list[tuple[int, int]]:
        """ Return list of ship cords """
        ship_cords = []
        for ship in self.ship_setup:
            ship_cords.extend(ship.get_co_ord())
        return ship_cords


@dataclass
class BattleShipGameModel:
    original_channel: TextChannel

    player_one: User
    player_one_setup_view: BattleshipSetupGridView
    player_one_grid: BattleShipGrid
    player_one_setup_message: Message
    player_one_game_message: Message
    player_one_status_message: Message
    player_one_game_view: BattleShipGameGridView

    player_two: User
    player_two_setup_view: BattleshipSetupGridView
    player_two_grid: BattleShipGrid
    player_two_setup_message: Message
    player_two_game_message: Message
    player_two_status_message: Message
    player_two_game_view: BattleShipGameGridView

    turn: User

    player_one_status_view: BattleShipStatusView | None = None
    player_two_status_view: BattleShipStatusView | None = None
    player_one_done: DoneButton | None = None
    player_one_finish_setup: bool = False

    player_two_done: DoneButton | None = None
    player_two_finish_setup: bool = False

    status: BattleShipGameStatus = BattleShipGameStatus.SETUP
    lock: bool = False


class BattleShipGameManager:

    @staticmethod
    def set_game(
            bot: Client,
            lobby_id: int,
            battle_ship_game_model: BattleShipGameModel
    ) -> None:
        bot.battleship_games[lobby_id] = battle_ship_game_model

    @staticmethod
    def get_game(bot: Client, lobby_id: int) -> BattleShipGameModel:
        lobbies: dict[int, BattleShipGameModel] = bot.battleship_games
        exists = lobbies.get(lobby_id)
        if exists is not None:
            return exists
        else:
            raise ValueError(f"Lobby with ID: {lobby_id} does not exist")

    @staticmethod
    def add_ship(
            bot: Client,
            lobby_id: int,
            co_ord: tuple[int, int],
            user: User
    ) -> None:
        """ Add ship to grid """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model is None:
            return
        if game_model.player_one.id == user.id:
            game_model.player_one_grid.add_ship(co_ord)
        else:
            game_model.player_two_grid.add_ship(co_ord)

    @staticmethod
    def get_cell_status(
            bot: Client,
            lobby_id: int,
            co_ord: tuple[int, int],
            user: User
    ) -> BattleShipCellStatus | None:
        """ Get cell status """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model is None:
            return None
        if user.id == game_model.player_one.id:
            return game_model.player_one_grid.get_cell_status(co_ord)
        else:
            return game_model.player_two_grid.get_cell_status(co_ord)

    @staticmethod
    def get_player_view_message(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> Message | None:
        """ Get player board """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model is None:
            return None
        if user.id == game_model.player_one.id:
            return game_model.player_one_game_message
        else:
            return game_model.player_two_game_message

    @staticmethod
    def get_player_setup_view(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> BattleshipSetupGridView:
        """ Get player board """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_one_setup_view
        else:
            return game_model.player_two_setup_view

    @staticmethod
    def get_player_setup_message(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> Message:
        """ Get player board """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_one_setup_message
        else:
            return game_model.player_two_setup_message

    @staticmethod
    def get_player_game_view(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> BattleShipGameGridView:
        """ Get player board """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            view = game_model.player_one_game_view
        else:
            view = game_model.player_two_game_view
        if view is None:
            raise Exception("View was not assigned")
        return view

    @staticmethod
    def toggle_player_done(
            bot: Client,
            lobby_id: int,
            user: User,
    ) -> bool:
        """ Set player done view """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            game_model.player_one_finish_setup = (
                not game_model.player_one_finish_setup
            )
            return game_model.player_one_finish_setup
        else:
            game_model.player_two_finish_setup = (
                not game_model.player_two_finish_setup
            )
            return game_model.player_two_finish_setup

    @staticmethod
    def set_game_status(
            bot: Client,
            lobby_id: int,
            status: BattleShipGameStatus
    ) -> None:
        """ Set game status """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        game_model.status = status

    @staticmethod
    def set_player_status_view(bot: Client, lobby_id: int, user: User, status_view: BattleShipStatusView) -> None:
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            game_model.player_one_status_view = status_view
        else:
            game_model.player_two_status_view = status_view

    @staticmethod
    def get_player_status_message(bot: Client, lobby_id: int, user: User) -> Message:
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_one_status_message
        else:
            return game_model.player_two_status_message

    @staticmethod
    def get_game_status(bot: Client, lobby_id: int) -> BattleShipGameStatus:
        """ Get game status """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        return game_model.status

    @staticmethod
    def get_player_grid(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> BattleShipGrid:
        """ Get player grid """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_one_grid
        else:
            return game_model.player_two_grid

    @staticmethod
    def get_opponent_grid(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> BattleShipGrid:
        """ Get opponent grid """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_two_grid
        else:
            return game_model.player_one_grid

    @staticmethod
    def set_player_done_button(
            bot: Client,
            lobby_id: int,
            user: User,
            button: Button[Any]
    ) -> None:
        """ Set player one view """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            game_model.player_one_done = button
        else:
            game_model.player_two_done = button

    @staticmethod
    def get_player_done_button(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> DoneButton | None:
        """ Get player one view """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_one_done
        else:
            return game_model.player_two_done

    @staticmethod
    def get_original_channel(
            bot: Client,
            lobby_id: int
    ) -> TextChannel:
        """ Get original channel """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        return game_model.original_channel

    @staticmethod
    def get_turn(
            bot: Client,
            lobby_id: int
    ) -> User:
        """ Get turn """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        return game_model.turn

    @staticmethod
    async def set_turn(
            bot: Client,
            lobby_id: int,
    ) -> None:
        """ Set turn """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model.turn.id == game_model.player_one.id:
            game_model.turn = game_model.player_two
        else:
            game_model.turn = game_model.player_one

    @staticmethod
    async def start(
            bot: Client,
            lobby_id: int
    ) -> None:
        """ Start game """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model.player_one_finish_setup and game_model.player_two_finish_setup:
            # Enable game grids
            game_model.player_one_game_view.enable()
            await BattleShipGameManager.get_player_view_message(
                bot,
                lobby_id,
                game_model.player_one
            ).edit(
                view=cast(View, game_model.player_one_game_view)
            )
            # Assign player one to turn
            game_model.turn = game_model.player_one
            await BattleShipGameManager.update_status_message(
                bot,
                lobby_id
            )

    @staticmethod
    async def update_status_message(bot: Client, lobby_id: int) -> None:
        """Update both player status views"""
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        game_model.player_one_status_view.update()
        game_model.player_two_status_view.update()
        await game_model.player_one_status_message.edit(
            content=None,
            view=game_model.player_one_status_view
        )
        await game_model.player_two_status_message.edit(
            content=None,
            view=game_model.player_two_status_view
        )

    @staticmethod
    def set_setup_done(
            bot: Client,
            lobby_id: int,
            user: User,
    ) -> None:
        """ Set setup done """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            game_model.player_one_finish_setup = True
        else:
            game_model.player_two_finish_setup = True

    @staticmethod
    def get_setup_done(
            bot: Client,
            lobby_id: int,
    ) -> bool:
        """ Get setup done """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        return game.player_one_finish_setup and game.player_two_finish_setup

    @staticmethod
    def get_hits(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> int:
        """ Get hits """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_two_grid.hits
        else:
            return game_model.player_one_grid.hits

    @staticmethod
    def get_status_hits(
            bot: Client,
            lobby_id: int,
            user: User
    ) -> int:
        """ Return status """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if user.id == game_model.player_one.id:
            return game_model.player_two_grid.hits
        else:
            return game_model.player_one_grid.hits

    @staticmethod
    def is_game_over(
            bot: Client,
            lobby_id: int,
    ) -> bool:
        """ Is game over """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model.player_one_grid.hits == 10 or game_model.player_two_grid.hits == 10:
            # Create new winner button to replace status.
            game_model.status = BattleShipGameStatus.FINISHED
            return True
        else:
            return False

    @staticmethod
    async def game_over(bot: Client, lobby_id: int) -> None:
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        winner_id = BattleShipGameManager.get_winner(bot, lobby_id)
        # If finished get the other view and update it with ships not hit
        if winner_id != game_model.player_one.id:
            loser_view = game_model.player_one_game_view
            loser_message = game_model.player_one_game_message
        else:
            loser_view = game_model.player_two_game_view
            loser_message = game_model.player_two_game_message

        await BattleShipGameManager.update_status_message(bot, lobby_id)

        loser_view.set_loser_board()
        await loser_message.edit(
            content=None,
            view=cast(View, loser_view)
        )
        # Stop all views
        if game_model.player_one_game_view:
            game_model.player_one_game_view.stop()
        if game_model.player_two_game_view:
            game_model.player_two_game_view.stop()
        if game_model.player_one_status_view:
            game_model.player_one_status_view.stop()
        if game_model.player_two_status_view:
            game_model.player_two_status_view.stop()
        # Delete lobby
        lobbies: dict[int, BattleShipGameModel] = bot.battleship_games
        lobbies.pop(lobby_id)

    @staticmethod
    def get_winner(bot: Client, lobby_id: int) -> int:
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        winner_id = None
        if game_model.player_one_grid.hits == 10:
            winner_id = game_model.player_two.id
        elif game_model.player_two_grid.hits == 10:
            winner_id = game_model.player_one.id
        return winner_id

    @staticmethod
    def get_loser_ship_co_ords(bot: Client, lobby_id: int) -> list[tuple[int, int]]:
        """ Get player ship ords """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        loser_grid = None
        if game_model.player_one_grid.hits == 10:
            loser_grid = game_model.player_two_grid
        elif game_model.player_two_grid.hits == 10:
            loser_grid = game_model.player_one_grid
        if loser_grid:
            return loser_grid.game_over()
        else:
            raise ValueError("Loser Grid not found.")
