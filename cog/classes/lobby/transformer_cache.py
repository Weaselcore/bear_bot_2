from api.models import GameModel
from cog.classes.utils import set_logger


class TransformerCache:
    def __init__(self) -> None:
        self._cache: dict[str, list[GameModel]] = dict()
        self.logger = set_logger("transformer_cache")

    def get(self, key: str) -> list[GameModel]:
        self.logger.info(f"Fetching from cache with key: {key}")
        return self._cache[key]
    
    def set(self, key: str, value) -> None:
        self.logger.info(f"Setting key: {key} with value: {value}")
        self._cache[key] = value

    def clear(self) -> None:
        self.logger.info("Cache cleared")
        self._cache.clear()
    
    def __repr__(self) -> str:
        cache_repr = ',\n'.join([f"    '{key}': {value}" for key, value in self._cache.items()])
        return f"TransformerCache(\n{cache_repr}\n)"
