
from dataclasses import dataclass
import pathlib
import json


@dataclass
class GameModel:
    game_code: str
    game_name: str
    max_size: int
    role: int
    icon_url: str = None

    def to_json(self) -> None:
        """ Serialize object into json """
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

    def to_object(self, data):
        """ Deserialize json into object """
        return json.loads(data, object_hook=lambda d: GameModel(**d))


class GameManager:
    def __init__(self) -> None:
        self.path = pathlib.Path('data/games.json')
        self.games = self.load_games()

    def load_games(self) -> list[GameModel]:
        """ Load games from json file """
        try:
            with open(self.path, 'r') as f:
                data = f.read()
                return [GameModel(**game) for game in json.loads(data)]
        except FileNotFoundError:
            return []

    def save_games(self) -> None:
        """ Save games to json file """
        with open(self.path, 'w+') as f:
            f.write(json.dumps([game.__dict__ for game in self.games], indent=4))

    def add_game(
        self,
        game_code: str,
        game_name: str,
        max_size: int,
        role: int,
        icon_url: str
    ) -> None:
        """ Add game to list """
        self.games.append(GameModel(game_code, game_name, max_size, role, icon_url))
        self.save_games()

    def remove_game(self, game_code: str) -> None:
        """ Remove game from list """
        for game in self.games:
            if game.game_code == game_code:
                self.games.remove(game)
                self.save_games()

    def get_max_size(self, game_code: str) -> int:
        """ Get max size of game """
        for game in self.games:
            if game.game_code == game_code:
                return game.max_size

    def get_game(self, game_code: str) -> GameModel:
        """ Get game from list """
        for game in self.games:
            if game.game_code == game_code:
                return game
