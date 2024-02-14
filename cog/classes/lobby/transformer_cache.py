from api.models import GameModel
from cog.classes.utils import set_logger


class TransformerCache:
    def __init__(self) -> None:
        self._cache: dict[str, list[GameModel]] = dict()
        self.logger = set_logger("transformer_cache")

    def get(self, guild_id: str) -> list[GameModel]:
        self.logger.info(f"Fetching from cache with guild_id: {guild_id}")
        self.logger.info(self._cache.__repr__())
        return self._cache.get(guild_id)
    
    def set(self, guild_id: str, game_model: GameModel) -> None:
        self.logger.info(f"Setting key: {guild_id} with value: {game_model}")
        game_list = self._cache.setdefault(guild_id, [])
        # The game model doesn't update, so they either exist or not.
        if game_model in game_list:
            self.logger.info(f"Game with ID: {game_model.id} found, skipping caching.")
            return
        game_list.append(game_model)
        self.logger.info(self._cache.__repr__())

    def remove(self, guild_id: str, game_id: str) -> None:
        self.logger.info(f"Removing cached data with key: {game_id}")
        try:
            games_list = self._cache.get(guild_id)
            if games_list is None:
                self.logger.warning(f"No cached data found for guild ID: {guild_id}")
                return
            game = next((game for game in games_list if game.id == int(game_id)))
            games_list.remove(game)
            self.logger.info(self._cache.__repr__())
        except KeyError as e:
            self.logger.error(e)
        except StopIteration as e:
            self.logger.error(e)      

    def clear(self) -> None:
        self.logger.info("Cache cleared")
        self._cache.clear()
    
    def __repr__(self) -> str:
        cache_repr = ',\n'.join([f"\n    '{key}': {value}" for key, value in self._cache.items()])
        return f"TransformerCache(\n{cache_repr}\n)"
