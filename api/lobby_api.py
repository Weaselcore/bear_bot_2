import os
from typing import Type, TypeAlias, TypeVar, Union, cast
import aiohttp
from pydantic import ValidationError
from api.api_error import GamesNotFound, LobbiesNotFound
from api.models import (
    GameModel,
    GameResponseModel,
    InsertGameModel,
    InsertLobbyModel,
    ListResponseModel,
    LobbyModel,
    LobbyResponseModel,
    MemberModel,
    MessageResponseModel,
    MultipleGameResponseModel,
    MultipleLobbyResponseModel,
    SingleResponseModel,
)

from api.session_manager import ClientSessionManager
from cog.classes.utils import set_logger


LOBBY_SERVER_ADDRESS = os.environ["LOBBY_SERVER_ADDRESS"]
LOBBY_API_AUTH_KEY = os.environ["LOBBY_API_AUTH_KEY"]
BASE_API_URL = f"http://{LOBBY_SERVER_ADDRESS}"

ModelType = TypeVar(
    "ModelType",
    GameModel,
    list[GameModel],
    LobbyModel,
    list[LobbyModel],
)

ResponseType = TypeVar(
    "ResponseType",
    GameResponseModel,
    MultipleGameResponseModel,
    LobbyResponseModel,
    MultipleLobbyResponseModel,
)


def unwrap_response(
    response: ResponseType,
) -> tuple[Union[GameModel, list[GameModel], LobbyModel, list[LobbyModel]], MessageResponseModel]:
    return response.data, response.message


class LobbyApi:
    def __init__(self, session_manager: ClientSessionManager):
        self.logger = set_logger(logger_name="lobby_api")
        self._session_manager = session_manager

    async def _request(  # type: ignore
        self,
        method: str,
        endpoint: str,
        return_type: Type[ResponseType],
        *args,
        **kwargs,
    ) -> tuple[ModelType, MessageResponseModel]:
        session = self._session_manager.session
        headers = {
            "x-api-key": f"{LOBBY_API_AUTH_KEY}",
            "Content-Type": "application/json",
        }
        try:
            async with session.request(
                method, BASE_API_URL + endpoint, headers=headers, *args, **kwargs
            ) as response:
                response.raise_for_status()  # Raise an error for non-2xx status codes
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    data = await response.json()
                    if isinstance(return_type, MultipleGameResponseModel):
                        if data == []:
                            raise GamesNotFound
                        return unwrap_response(
                            MultipleGameResponseModel.model_validate(
                                data, from_attributes=True
                            )
                        )
                    elif isinstance(return_type, MultipleLobbyResponseModel):
                        if data == []:
                            raise LobbiesNotFound
                        return unwrap_response(
                            MultipleLobbyResponseModel.model_validate(
                                data, from_attributes=True
                            )
                        )
                    elif isinstance(return_type, GameModel):
                        return unwrap_response(
                            GameResponseModel.model_validate(data, from_attributes=True)
                        )
                    elif isinstance(return_type, LobbyModel):
                        return unwrap_response(
                            LobbyResponseModel.model_validate(
                                data, from_attributes=True
                            )
                        )
                    else:
                        raise NotImplementedError("This type has no implementations.")
                else:
                    error_message = await response.text()
                    raise Exception(f"Non-JSON response: {error_message}")
        except aiohttp.ClientResponseError as e:
            # Handle client-side errors (e.g., 4xx status codes)
            self.logger.error(f"Client error: {e.status} - {e.message}")
        except aiohttp.ServerDisconnectedError as e:
            # Handle server disconnected errors
            self.logger.error(f"Server disconnected error: {e}")
        except aiohttp.ServerTimeoutError as e:
            # Handle server timeout errors
            self.logger.error(f"Server timeout error: {e}")
        except aiohttp.ClientConnectionError as e:
            # Handle connection errors (e.g., network issues)
            self.logger.error(f"Connection error: {e}")
        except aiohttp.ClientError as e:
            # Handle other aiohttp client errors
            self.logger.error(f"An error occurred: {e}")
        except ValidationError as e:
            # Handle validation errors
            for error in e.errors():
                self.logger.error(f"Error in field '{error['loc'][0]}': {error['msg']}")
        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error(e)
            raise e

    """
    Lobby API methods
    """

    async def get_lobbies(self) -> tuple[list[LobbyModel], MessageResponseModel]:
        return await self._request("GET", "/api/Lobby/", MultipleLobbyResponseModel)

    async def get_lobby(self, lobby_id: int) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request("GET", f"/api/Lobby/{lobby_id}", LobbyResponseModel)

    async def get_lobby_by_owner_id(
        self, owner_id: int
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "GET", f"/api/Lobby/ownerId/{owner_id}", LobbyResponseModel
        )

    async def post_lobby(
        self, lobby: InsertLobbyModel
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "POST",
            f"/api/Lobby",
            LobbyResponseModel,
            data=lobby.model_dump_json(),
        )

    async def put_lobby(
        self, lobby: LobbyModel
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "PUT",
            f"/api/Lobby/{lobby.id}",
            LobbyResponseModel,
            data=lobby.model_dump_json(),
        )

    async def delete_lobby(
        self, lobby_id: int
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "DELETE",
            f"/api/Lobby/{lobby_id}",
            LobbyResponseModel,
        )

    """
    MemberModel API methods
    """

    async def post_member(
        self, lobby_id: int, member: MemberModel
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "POST",
            f"/api/Member/{lobby_id}",
            LobbyResponseModel,
            data=member.model_dump_json(),
        )

    async def put_member(
        self,
        lobby_id: int,
        member: MemberModel,
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "PUT",
            f"/api/Member/{lobby_id}/{member.id}",
            LobbyResponseModel,
            json=member.model_dump_json(),
        )

    async def put_joined_vc(
        self, lobby_id: int, member_id: int
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "PUT",
            f"/api/Member/{lobby_id}/join-vc/{member_id}",
            LobbyResponseModel,
        )

    async def toggle_member_ready(
        self, member_id: int, lobby_id: int
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "PUT",
            f"/api/Member/{lobby_id}/toggle-ready/{member_id}",
            LobbyResponseModel,
        )

    async def delete_member(
        self, member_id: int, lobby_id: int
    ) -> tuple[LobbyModel, MessageResponseModel]:
        return await self._request(
            "DELETE",
            f"/api/Member/{lobby_id}/{member_id}",
            LobbyResponseModel,
        )

    """
    Game API methods
    """

    async def get_games(self) -> tuple[list[GameModel], MessageResponseModel]:
        return await self._request(
            "GET",
            "/api/Game/",
            MultipleGameResponseModel,
        )

    async def get_game(self, game_id: int) -> tuple[GameModel, MessageResponseModel]:
        return await self._request(
            "GET",
            f"/api/Game/{game_id}",
            GameResponseModel,
        )

    async def get_games_by_guild_id(
        self, guild_id: int
    ) -> tuple[list[GameModel], MessageResponseModel]:
        return await self._request(
            "GET",
            f"/api/Game/guild/{guild_id}",
            MultipleGameResponseModel,
        )

    async def post_game(
        self, game: InsertGameModel
    ) -> tuple[GameModel, MessageResponseModel]:
        return await self._request(
            "POST",
            "/api/Game",
            GameResponseModel,
            data=game.model_dump_json(),
        )

    async def put_game(self, game: GameModel) -> tuple[GameModel, MessageResponseModel]:
        return await self._request(
            "PUT",
            f"/api/Game/{game.id}",
            GameResponseModel,
            data=game.model_dump_json(),
        )

    async def delete_game(self, game_id: int) -> tuple[GameModel, MessageResponseModel]:
        return await self._request(
            "DELETE",
            f"/api/Game/{game_id}",
            GameResponseModel,
        )
