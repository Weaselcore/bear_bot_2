from collections.abc import Sequence

import discord

from embeds.game_embed import GameEmbedManager
from repository.game_repo import GamePostgresRepository
from repository.tables import GameModel


class GameManager:

    def __init__(
        self,
        repository: GamePostgresRepository,
        embed_manager: GameEmbedManager,
        bot: discord.Client
    ) -> None:
        self._repository = repository
        self.bot = bot
        self.embed_manager = embed_manager

    def _get_repository(self) -> GamePostgresRepository:
        if self._repository:
            return self._repository
        else:
            raise AttributeError('Repository has not been set')

    async def add_game(
        self,
        game_name: str,
        guild_id: int,
        guild_name: str,
        max_size: int,
        role: int | None,
        icon_url: str | None
    ) -> int:
        """ Add game to list """
        game_id = await self._get_repository().create_game(
            name=game_name,
            max_size=max_size,
            role=role,
            icon_url=icon_url,
            guild_id=guild_id,
            guild_name=guild_name
        )
        return game_id

    async def remove_game(self, game_id: int) -> bool:
        """ Remove game from list """
        await self._get_repository().delete_game(game_id)
        try:
            game = await self._get_repository().get_game(game_id)
            return False if game is None else True
        except ValueError:
            return True

    async def get_max_size(self, game_id: int) -> int:
        """ Get max size of game """
        return await self._get_repository().get_game_max_size(game_id)

    async def get_game(self, game_id: int) -> GameModel:
        """ Get game from list """
        return await self._get_repository().get_game(game_id)

    async def get_all_games_by_guild_id(self, guild_id: int) -> Sequence[GameModel]:
        """ Get all games names and id from list of GameModels """
        return await self._get_repository().get_all_games_by_guild_id(guild_id)

    async def get_max_size_by_name(self, game_name: str, guild_id: int) -> int | None:
        """ Get max size of game by id """
        return await self._get_repository().get_max_size_by_name(game_name, guild_id)
