import os
import aiohttp
from pydantic import ValidationError
from api.models import (
    GameModel,
    InsertGameModel,
    InsertLobbyModel,
    LobbyModel,
    MemberLobbyModel,
    MemberModel,
)

from api.session_manager import ClientSessionManager
from cog.classes.utils import set_logger
from exceptions.lobby_exceptions import (
    DeletedGame,
    DeletedLobby,
    LobbyNotFoundByOwnerId,
)

LOBBY_SERVER_ADDRESS = os.environ["LOBBY_SERVER_ADDRESS"]
LOBBY_API_AUTH_KEY = os.environ["LOBBY_API_AUTH_KEY"]
BASE_API_URL = f"http://{LOBBY_SERVER_ADDRESS}"


class LobbyApi:
    def __init__(self, session_manager: ClientSessionManager):
        self.logger = set_logger(logger_name="lobby_api")
        self._session_manager = session_manager

    async def _request(
        self, method: str, endpoint: str, model_cls: type, *args, **kwargs
    ):
        session = self._session_manager.session
        headers = {"x-api-key": f"{LOBBY_API_AUTH_KEY}"}
        try:
            async with session.request(
                method, BASE_API_URL + endpoint, headers=headers, *args, **kwargs
            ) as response:
                response.raise_for_status()  # Raise an error for non-2xx status codes
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    data = await response.json()
                    if data is None:
                        if model_cls is LobbyModel:
                            raise DeletedLobby("Lobby has been deleted.")
                        if model_cls is GameModel:
                            raise DeletedGame("Game has been deleted.")
                        return None  # Return None when data is None
                    if isinstance(data, list):
                        return [model_cls(**item) for item in data]
                    else:
                        return model_cls(**data)
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
            self.logger.error(f"Unexpected error: {e}")

    """
    Lobby API methods
    """

    async def get_lobbies(self) -> list[LobbyModel]:
        return await self._request("GET", "/api/Lobby/", LobbyModel)

    async def get_lobby(self, lobby_id: int) -> LobbyModel:
        return await self._request("GET", f"/api/Lobby/{lobby_id}", LobbyModel)

    async def get_lobby_by_owner_id(self, owner_id: int) -> LobbyModel:
        try:
            return await self._request(
                "GET", f"/api/Lobby/ownerId/{owner_id}", LobbyModel
            )
        except Exception:
            raise LobbyNotFoundByOwnerId

    async def post_lobby(self, lobby: InsertLobbyModel) -> LobbyModel:
        return await self._request(
            "POST", f"/api/Lobby", LobbyModel, json=lobby.model_dump_json()
        )

    async def put_lobby(self, lobby_id: int, lobby: LobbyModel) -> LobbyModel:
        return await self._request(
            "PUT", f"/api/Lobby/{lobby_id}", LobbyModel, json=lobby.model_dump_json()
        )

    async def delete_lobby(self, lobby_id: int) -> None:
        await self._request("DELETE", f"/api/Lobby/{lobby_id}", LobbyModel)

    """
    MemberModel API methods
    """

    async def post_member(self, member: MemberModel) -> MemberModel:
        return await self._request(
            "POST", "/api/Member", MemberModel, json=member.model_dump_json()
        )

    async def put_member(
        self, member_id: int, lobby_id: int, member: MemberModel
    ) -> MemberModel:
        return await self._request(
            "PUT",
            f"/api/Member/{lobby_id}/{member_id}",
            MemberModel,
            json=member.model_dump_json(),
        )

    async def toggle_member_ready(
        self, member_id: int, lobby_id: int
    ) -> MemberLobbyModel:
        return await self._request(
            "PUT", f"/api/Member/{lobby_id}/toggle-ready/{member_id}", MemberLobbyModel
        )

    async def delete_member(self, member_id: int, lobby_id: int) -> None:
        await self._request(
            "DELETE", f"/api/Member/{lobby_id}/{member_id}", MemberModel
        )

    """
    Game API methods
    """

    async def get_games(self) -> list[GameModel]:
        return await self._request("GET", "/api/Game/", GameModel)

    async def get_game(self, game_id: int) -> GameModel:
        return await self._request("GET", f"/api/Game/{game_id}", GameModel)

    async def get_games_by_guild_id(self, guild_id: int) -> list[GameModel]:
        return await self._request("GET", f"/api/Game/guild/{guild_id}", GameModel)

    async def post_game(self, game: InsertGameModel) -> GameModel:
        return await self._request(
            "POST", "/api/Game", GameModel, json=game.model_dump_json()
        )

    async def put_game(self, game_id: int, game: GameModel) -> GameModel:
        return await self._request(
            "PUT", f"/api/Game/{game_id}", GameModel, json=game.model_dump_json()
        )

    async def delete_game(self, game_id: int) -> None:
        await self._request("DELETE", f"/api/Game/{game_id}", GameModel)
