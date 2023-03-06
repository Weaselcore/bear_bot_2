from collections.abc import Sequence
from sqlalchemy import Result, delete, insert, select, update
from repository.tables import GameModel, GuildModel


class GamePostgresRepository:
    def __init__(self, session):
        self.database = session

    async def create_game(
        self,
        name: str,
        max_size: int,
        guild_id: int,
        guild_name: str,
        role: int | None = None,
        icon_url: str | None = None,
    ) -> int:
        async with self.database() as session:

            result: Result = await session.execute(
                select( # type: ignore
                    GuildModel.id
                ).filter(
                    GuildModel.id == guild_id
                )
            )
            exists = result.scalars().first() # type: ignore
            if exists is None:
                await session.execute(
                    insert(
                        GuildModel
                    ).values(
                        id=guild_id,
                        name=guild_name,
                    )
                )

            new_game = GameModel(
                    name=name,
                    guild_id=guild_id,
                    max_size=max_size,
                    role=role,
                    icon_url=icon_url,
                )
            session.add(new_game)
            await session.commit()
            return new_game.id

    async def delete_game(self, game_id: int) -> None:
        async with self.database() as session:
            result: Result = await session.execute(
                delete(
                    GameModel
                ).where(
                    GameModel.id == game_id
                )
            )
            print(result)
            await session.commit()

    async def get_game(self, game_id: int) -> GameModel:
        async with self.database() as session:
            result: Result = await session.execute(
                select(
                    GameModel
                ).filter(
                    GameModel.id == game_id
                )
            )
            game = result.scalars().first()
            if game is None:
                raise ValueError(f"Game code {game_id} not found.")
            return game

    async def get_game_max_size(self, game_id: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                select(
                    GameModel.max_size
                ).filter(
                    GameModel.id == game_id
                )
            )
            game_size = result.scalars().first()
            if game_size is None:
                raise ValueError(f"Game code {game_id} not found.")
            return game_size
            
    async def get_game_name(self, game_id: int) -> str:
        async with self.database() as session:
            result: Result = session.execute(
                select(
                    GameModel.name
                ).filter(
                    GameModel.id == game_id
                )
            )
            game_name = result.scalars().first()
            if game_name is None:
                raise ValueError(f"Game code {game_id} not found.")
            return game_name

    async def set_game_name(self, game_id: int, name: str) -> str:
        async with self.database() as session:
            result: Result = await session.execute(
                update( # type: ignore
                    GameModel
                ).where(
                    GameModel.id == game_id
                ).values(
                    name=name
                ).returning(
                    GameModel.name
                )
            )
            game_name = result.scalars().first()
            if game_name is None:
                raise ValueError(f"Game code {game_id} not found.")
            session.commit()
            return game_name

    async def set_game_max_size(self, game_id: int, max_size: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                update( # type: ignore
                    GameModel
                ).where(
                    GameModel.id == game_id
                ).values(
                    max_size=max_size
                ).returning(
                    GameModel.max_size
                )
            )
            max_size = result.scalars().first() # type: ignore
            if max_size is None:
                raise ValueError(f"Game code {game_id} not found.")
            session.commit()
            return max_size

    async def get_game_icon_url(self, game_id: int, guild_id: int) -> str | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select( # type: ignore
                    GameModel.icon_url
                ).filter(
                    GameModel.id == game_id
                ).filter(
                    GameModel.guild_id == guild_id
                )
            )
            return result.scalars().first()

    async def set_game_icon_url(self, game_id: int, icon_url: str) -> int:
        async with self.database() as session:
            result: Result = session.execute(
                update( # type: ignore
                    GameModel
                ).where(
                    GameModel.id == game_id
                ).values(
                    icon_url=icon_url
                ).returning(
                    GameModel.icon_url
                )
            )
            max_size = result.scalars().first() # type: ignore
            if max_size is None:
                raise ValueError(f"Game code {game_id} not found.")
            session.commit()
            return max_size

    async def get_game_role(self, game_id: int) -> int | None:
        async with self.database() as session:
            result: Result = await session.execute(
                select(
                    GameModel.role
                ).filter(
                    GameModel.id == game_id
                )
            )
            game_role = result.scalars().first()
            if game_role is None:
                raise ValueError(f"Game code {game_id} not found.")
            return game_role

    async def set_game_role(self, game_id: int, role: int) -> int:
        async with self.database() as session:
            result: Result = await session.execute(
                update( # type: ignore
                    GameModel
                ).where(
                    GameModel.id == game_id
                ).values(
                    role=role
                ).returning(
                    GameModel.role
                )
            )
            game_role = result.scalars().first()
            if game_role is None:
                raise ValueError(f"Game code {game_id} not found.")
            session.commit()
            return game_role

    async def get_all_games_by_guild_id(self, guild_id: int) -> Sequence[GameModel]:
        """ Get all games name and id from list of GameModels """
        async with self.database() as session:
            result: Result = await session.execute(
                select(
                    GameModel
                ).filter(
                    GameModel.guild_id == guild_id
                )
            )
            game_list = result.scalars().fetchmany()
            return game_list

    async def get_max_size_by_name(self, game_name: str, guild_id: int) -> int | None:
        """ Get max size of game by id """
        async with self.database() as session:
            result: Result = await session.execute(
                select( # type: ignore
                    GameModel.max_size
                ).filter(
                    GameModel.guild_id == guild_id
                ).filter(
                    GameModel.name == game_name
                )
            )
            max_size = result.scalars().first()
            return max_size

    async def get_game_id_by_name(self, game_name: str, guild_id: int) -> int:
        """ Get game id by name """
        async with self.database() as session:
            result: Result = await session.execute(
                select( # type: ignore
                    GameModel.id
                ).filter(
                    GameModel.guild_id == guild_id
                ).filter(
                    GameModel.name == game_name
                )
            )
            game_id = result.scalars().first()
            if game_id is None:
                raise ValueError(f"{game_name} not found with guild id {guild_id}.")
            return game_id