
from dataclasses import dataclass
from enum import Enum

from discord.ui import View, Button
from discord import Message, Member, ButtonStyle, TextChannel
from discord.ext import commands


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
        self.origin: tuple[int, int] = None
        self._xy: list[tuple] = []
        self._orientation: list[ShipOrientation] = [
            ShipOrientation.EAST,
            ShipOrientation.SOUTH,
            ShipOrientation.WEST,
            ShipOrientation.NORTH,
            ShipOrientation.NONE
        ]
        self._current_orientation: int = 0

    def get_co_ord(self) -> list[tuple]:
        """ Get co-ordinates of ship """
        return self._xy

    def set_co_ord(self, co_ord: list[tuple]) -> None:
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

    def get_origin(self) -> tuple[int, int]:
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
        self.current_ship = patrol_boat
        self.status = BattleShipGameStatus.SETUP
        self.hits = 0

    def _calculate_co_ord(self, x: int, y: int, ship: Ship) -> bool:
        """ Calculate co-ordinates of ship """
        new_co_ords: list[tuple] = []
        vector = ship.get_orientation().value
        if vector is None:
            return False
        for number in range(ship.length):
            i = x + (number * vector[1])
            j = y + (number * vector[0])
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
                    self.grid[co_ord[0]][co_ord[1]
                                         ] = BattleShipCellStatus.SHIP_ORIGIN
                else:
                    self.grid[co_ord[0]][co_ord[1]] = BattleShipCellStatus.SHIP
            ship.set_co_ord(new_co_ords)
            return True

    def get_next_ship(self) -> Ship:
        """ Get next ship """
        for ship in self.ship_setup:
            if len(ship.get_co_ord()) == 0:
                return ship
        return None

    def get_ship_from_origin(self, co_ord: tuple[int, int]) -> Ship:
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
                self.grid[ship_co_ord[cell][0]][ship_co_ord[cell]
                                                [1]] = BattleShipCellStatus.EMPTY

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


@dataclass
class BattleShipGameModel:
    original_channel: TextChannel
    player_one: Member = None
    player_two: Member = None
    turn: Member = None

    player_one_setup_message: Message = None
    player_one_setup_view: View = None
    player_one_done: Button = None
    player_one_finish_setup: bool = False
    player_one_game_view: View = None

    player_two_setup_message: Message = None
    player_two_setup_view: View = None
    player_two_done: Button = None
    player_two_finish_setup: bool = False
    player_two_game_view: View = None

    player_one_grid: BattleShipGrid = None
    player_two_grid: BattleShipGrid = None

    game_view: View = None
    game_message: Message = None
    game_status_view: View = None
    game_status_message: Message = None
    status: BattleShipGameStatus = BattleShipGameStatus.SETUP
    lock: bool = False


class BattleShipGameManager:

    @staticmethod
    def set_game(
        bot: commands.Bot,
        lobby_id: int,
        battle_ship_game_model: BattleShipGameModel
    ) -> None:
        bot.battleship_games[lobby_id] = battle_ship_game_model

    @staticmethod
    def get_game(bot: commands.Bot, lobby_id: int) -> BattleShipGameModel:
        return bot.battleship_games[lobby_id]

    @staticmethod
    def add_ship(
        bot: commands.Bot,
        lobby_id: int,
        co_ord: tuple[int, int],
        member: Member
    ) -> None:
        """ Add ship to grid """
        game_model = BattleShipGameManager.get_game(bot, lobby_id)
        if game_model.player_one == member:
            game_model.player_one_grid.add_ship(co_ord)
        else:
            game_model.player_two_grid.add_ship(co_ord)

    @staticmethod
    def get_cell_status(
        bot: commands.Bot,
        lobby_id: int,
        co_ord: tuple[int, int],
        member: Member
    ) -> BattleShipCellStatus:
        """ Get cell status """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if member == game.player_one:
            return game.player_one_grid.get_cell_status(co_ord)
        else:
            return game.player_two_grid.get_cell_status(co_ord)

    @staticmethod
    def get_player_view_message(
        bot: commands.Bot,
        lobby_id: int,
        player: Member
    ) -> View:
        """ Get player board """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            return game.player_one_setup_message
        else:
            return game.player_two_setup_message

    @staticmethod
    def get_player_setup_view(
        bot: commands.Bot,
        lobby_id: int,
        player: Member
    ) -> View:
        """ Get player board """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            return game.player_one_setup_view
        else:
            return game.player_two_setup_view

    @staticmethod
    def set_player_game_view(
        bot: commands.Bot,
        lobby_id: int,
        player: Member,
        view: View
    ) -> Button:
        """ Get player board """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            bot.battleship_games[lobby_id].player_one_game_view = view
        else:
            bot.battleship_games[lobby_id].player_two_game_view = view

    @staticmethod
    def get_player_game_view(
        bot: commands.Bot,
        lobby_id: int,
    ) -> View:
        """ Get player board """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        member = game.turn
        if member == game.player_one:
            return game.player_one_game_view
        else:
            return game.player_two_game_view

    @staticmethod
    def toggle_player_done(
        bot: commands.Bot,
        lobby_id: int,
        player: Member,
    ) -> bool:
        """ Set player done view """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            bot.battleship_games[lobby_id].player_one_done = (
                not bot.battleship_games[lobby_id].player_one_done
            )
            return bot.battleship_games[lobby_id].player_one_done
        else:
            bot.battleship_games[lobby_id].player_two_done = (
                not bot.battleship_games[lobby_id].player_two_done
            )
            return bot.battleship_games[lobby_id].player_two_done

    @staticmethod
    def set_game_status(
        bot: commands.Bot,
        lobby_id: int,
        status: BattleShipGameStatus
    ) -> None:
        """ Set game status """
        bot.battleship_games[lobby_id].status = status

    @staticmethod
    def set_game_status_view(
        bot: commands.Bot,
        lobby_id: int,
        view: View
    ) -> None:
        """ Set game status """
        bot.battleship_games[lobby_id].game_status_view = view

    @staticmethod
    def get_game_status(bot: commands.Bot, lobby_id: int) -> BattleShipGameStatus:
        """ Get game status """
        return bot.battleship_games[lobby_id].status

    @staticmethod
    def get_player_grid(
        bot: commands.Bot,
        lobby_id: int,
        player: Member
    ) -> BattleShipGrid:
        """ Get player grid """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            return game.player_one_grid
        else:
            return game.player_two_grid

    @staticmethod
    def get_opponent_grid(
        bot: commands.Bot,
        lobby_id: int,
        player: Member
    ) -> BattleShipGrid:
        """ Get opponent grid """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            return game.player_two_grid
        else:
            return game.player_one_grid

    @staticmethod
    def set_player_done_button(
        bot: commands.Bot,
        lobby_id: int,
        player: Member,
        button: Button
    ) -> None:
        """ Set player one view """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            bot.battleship_games[lobby_id].player_one_done = button
        else:
            bot.battleship_games[lobby_id].player_two_done = button

    @staticmethod
    def get_player_done_button(
        bot: commands.Bot,
        lobby_id: int,
        player: Member
    ) -> Button:
        """ Get player one view """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            return game.player_one_done
        else:
            return game.player_two_done

    @staticmethod
    def get_original_channel(
        bot: commands.Bot,
        lobby_id: int
    ) -> TextChannel:
        """ Get original channel """
        return bot.battleship_games[lobby_id].original_channel

    @staticmethod
    def get_turn(
        bot: commands.Bot,
        lobby_id: int
    ) -> Member:
        """ Get turn """
        return bot.battleship_games[lobby_id].turn

    @staticmethod
    def set_turn(
        bot: commands.Bot,
        lobby_id: int,
    ) -> None:
        """ Set turn """
        if bot.battleship_games[lobby_id].turn == bot.battleship_games[lobby_id].player_one:
            bot.battleship_games[lobby_id].turn = bot.battleship_games[lobby_id].player_two
        else:
            bot.battleship_games[lobby_id].turn = bot.battleship_games[lobby_id].player_one

    @staticmethod
    async def start(
        bot: commands.Bot,
        lobby_id: int,
        game_status_message: Message,
        game_message: Message,
        game_grid_view1: View,
        game_grid_view2: View,
    ) -> None:
        """ Start game """
        bot.battleship_games[lobby_id].player_one_game_view = game_grid_view1
        bot.battleship_games[lobby_id].player_two_game_view = game_grid_view2
        bot.battleship_games[lobby_id].game_status_message = game_status_message
        bot.battleship_games[lobby_id].game_message = game_message
        await game_message.edit(
            view=BattleShipGameManager.get_player_game_view(bot, lobby_id)
        )

    @staticmethod
    async def update_game_message(
        bot: commands.Bot,
        lobby_id: int,
    ) -> None:
        """ Update game message """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        view = None
        if game.turn == game.player_one:
            view = game.player_one_game_view
        else:
            view = game.player_two_game_view
        await bot.battleship_games[lobby_id].game_message.edit(
            content=None,
            view=view
        )

    @staticmethod
    def get_game_status_message(
        bot: commands.Bot,
        lobby_id: int,
    ) -> Message:
        """ Get game status message """
        return bot.battleship_games[lobby_id].game_status_message

    @staticmethod
    def set_game_status_message(
        bot: commands.Bot,
        lobby_id: int,
        message: Message
    ) -> None:
        """ Set game status message """
        bot.battleship_games[lobby_id].game_status_message = message

    @staticmethod
    def set_setup_done(
        bot: commands.Bot,
        lobby_id: int,
        player: Member,
    ) -> None:
        """ Set setup done """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if player == game.player_one:
            bot.battleship_games[lobby_id].player_one_finish_setup = True
        else:
            bot.battleship_games[lobby_id].player_two_finish_setup = True

    @staticmethod
    def get_setup_done(
        bot: commands.Bot,
        lobby_id: int,
    ) -> bool:
        """ Get setup done """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        return game.player_one_finish_setup and game.player_two_finish_setup

    @staticmethod
    def get_game_message(
        bot: commands.Bot,
        lobby_id: int,
    ) -> Message:
        """ Get game message """
        return bot.battleship_games[lobby_id].game_message

    @staticmethod
    def set_game_message(
        bot: commands.Bot,
        lobby_id: int,
        message: Message,
    ) -> None:
        """ Set game message """
        bot.battleship_games[lobby_id].game_message = message

    @staticmethod
    def get_hits(
        bot: commands.Bot,
        lobby_id: int,
    ) -> int:
        """ Get hits """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if game.turn == game.player_one:
            return game.player_two_grid.hits
        else:
            return game.player_one_grid.hits

    @staticmethod
    def get_status(
        bot: commands.Bot,
        lobby_id: int,
    ) -> tuple:
        """ Return status """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        return (
            game.player_one.display_name,
            game.player_two_grid.hits,
            game.player_two.display_name,
            game.player_one_grid.hits
        )

    @staticmethod
    def is_game_over(
        bot: commands.Bot,
        lobby_id: int,
    ) -> bool:
        """ Is game over """
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if game.player_one_grid.hits == 10 or game.player_two_grid.hits == 10:
            # Create new winner button to replace status.
            game.status = BattleShipGameStatus.FINISHED
            return True
        else:
            return False

    @staticmethod
    def game_over(bot: commands.Bot, lobby_id: int) -> str:
        game = BattleShipGameManager.get_game(bot, lobby_id)
        if game.player_one_grid.hits == 10:
            winner = game.player_two.display_name
        elif game.player_two_grid.hits == 10:
            winner = game.player_one.display_name

        # Stop all views
        game.game_status_view.stop()
        game.player_one_game_view.stop()
        game.player_two_game_view.stop()
        # Delete lobby
        bot.battleship_games.pop(lobby_id)

        return winner

    @staticmethod
    def set_lock(
        bot: commands.Bot,
        lobby_id: int
    ) -> None:
        """ Set lock """
        bot.battleship_games[lobby_id].lock = True

    @staticmethod
    def release_lock(
        bot: commands.Bot,
        lobby_id: int
    ) -> None:
        """ Release lock """
        bot.battleship_games[lobby_id].lock = False

    @staticmethod
    def get_lock(
        bot: commands.Bot,
        lobby_id: int
    ) -> None:
        """ Set lock """
        return bot.battleship_games[lobby_id].lock
