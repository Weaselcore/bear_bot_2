from functools import wraps
from api.models import LobbyModel, LobbyModel
from cog.classes.utils import set_logger


class LobbyCache:
    def __init__(self) -> None:
        self._cache: dict[str, list[LobbyModel]] = dict()
        self.logger = set_logger("lobby_cache")

    def __call__(self, func):
        """
        Decorator that will capture the result and add it to the cache.
        """
        @wraps(func)
        async def wrapper(instance, *args, **kwargs):
            result: LobbyModel | list[LobbyModel] = await func(instance, *args, **kwargs)
            if isinstance(result, LobbyModel):
                self.set(str(result.guild_id), result)
                return result
            elif isinstance(result, list) and all(isinstance(item, LobbyModel) for item in result):
                for lobby_model in result:
                    self.set(str(lobby_model.guild_id), lobby_model)
                return result
            else:
                instance.logger.warning(f"Returned data is not an instance of LobbyModel or a list of LobbyModels.")
                return None
        return wrapper

    def get(self, guild_id: str) -> list[LobbyModel] | None:
        self.logger.info(f"Fetching from cache with guild_id: {guild_id}")
        self.logger.info(self._cache.__repr__())
        return self._cache.get(guild_id)
    
    def set(self, guild_id: str, lobby_model: LobbyModel) -> None:
        self.logger.info(f"Setting key: {guild_id} with value: {lobby_model}")
        lobby_list = self._cache.setdefault(guild_id, [])
        # The lobby model doesn't update, so they either exist or not.
        if lobby_model in lobby_list:
            self.logger.info(f"Lobby with ID: {lobby_model.id} found, skipping caching.")
            return
        lobby_list.append(lobby_model)
        self.logger.info(self._cache.__repr__())

    def remove(self, guild_id: str, lobby_id: str) -> None:
        self.logger.info(f"Removing cached data with key: {lobby_id}")
        try:
            lobby_list = self._cache.get(guild_id)
            if lobby_list is None:
                self.logger.warning(f"No cached data found for guild ID: {guild_id}")
                return
            lobby = next((lobby for lobby in lobby_list if lobby.id == int(lobby_id)))
            lobby_list.remove(lobby)
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
        return f"LobbyCache(\n{cache_repr}\n)"
