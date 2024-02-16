from functools import wraps
from api.models import LobbyModel, LobbyModel
from cog.classes.utils import set_logger


class LobbyCache:
    def __init__(self) -> None:
        self._cache: dict[str, LobbyModel] = dict()
        self.logger = set_logger("lobby_cache")

    def __call__(self, func):
        """
        Decorator that will capture the result and add it to the cache.
        """
        @wraps(func)
        async def wrapper(instance, *args, **kwargs):
            result: LobbyModel | list[LobbyModel] = await func(instance, *args, **kwargs)
            if isinstance(result, LobbyModel):
                self.set(str(result.id), result)
                return result
            elif isinstance(result, list) and all(isinstance(item, LobbyModel) for item in result):
                for lobby_model in result:
                    self.set(str(lobby_model.id), lobby_model)
                return result
            else:
                instance.logger.warning(f"Returned data is not an instance of LobbyModel or a list of LobbyModels.")
                return None
        return wrapper

    def get(self, lobby_id: str) -> LobbyModel | None:
        self.logger.info(f"Fetching from cache with lobby: {lobby_id}")
        self.logger.info(self._cache.__repr__())
        lobby = self._cache.get(lobby_id)
        return lobby
    
    def set(self, lobby_id: str, lobby_model: LobbyModel) -> None:
        self.logger.info(f"Setting key: {lobby_id} with value: {lobby_model}")
        lobby = self._cache.get(lobby_id)
        self._cache[str(lobby_id)] = lobby_model
        self.logger.info(self._cache.__repr__())

    def remove(self, lobby_id: str) -> None:
        self.logger.info(f"Removing cached data with key: {lobby_id}")
        try:
            lobby = self._cache.get(lobby_id)
            if lobby is None:
                self.logger.warning(f"No cached data found for lobby ID: {lobby_id}")
                return
            self.logger.info(self._cache.__repr__())
            self._cache.pop(lobby_id)
        except KeyError as e:
            self.logger.error(e)
        except StopIteration as e:
            self.logger.error(e)      

    def clear(self) -> None:
        self.logger.info("Cache cleared")
        self._cache.clear()
    
    def __repr__(self) -> str:
        cache_repr = ',\n'.join([f"\n    '{key}': {value}" for key, value in self._cache.items()])
        return f"LobbyCache(\n{cache_repr}\n)"
