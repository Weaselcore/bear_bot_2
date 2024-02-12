import os
import aiohttp
from api.models import Game, Lobby, Member

from api.session_manager import ClientSessionManager
from cog.classes.utils import set_logger

LOBBY_SERVER_ADDRESS = os.environ["LOBBY_SERVER_ADDRESS"]
API_AUTH_KEY = os.environ["API_AUTH_KEY"]
BASE_API_URL = f"http://{LOBBY_SERVER_ADDRESS}"


class LobbyApi:
    def __init__(self, session_manager: ClientSessionManager):
        self.logger = set_logger(logger_name="lobby_api")
        self._session_manager = session_manager

    async def _request(
        self, method: str, endpoint: str, model_cls: type, *args, **kwargs
    ):
        session = self._session_manager.session
        headers = {"Authorization": f"Bearer {API_AUTH_KEY}"}
        try:
            async with getattr(session, method.lower())(
                BASE_API_URL + endpoint, headers=headers, *args, **kwargs
            ) as response:
                if method.lower() == "get":
                    data = await response.json()
                    if isinstance(data, list):
                        return [model_cls(**item) for item in data]
                    else:
                        return model_cls(**data)
                else:
                    return None  # For non-GET requests
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
        except Exception as e:
            # Handle any other unexpected errors
            self.logger.error(f"Unexpected error: {e}")

    """
    Lobby API methods
    """

    async def get_lobbies(self) -> list[Lobby]:
        return await self._request("GET", "/api/Lobby/", Lobby)

    async def get_lobby(self, lobby_id: int) -> Lobby:
        return await self._request("GET", f"/api/Lobby/{lobby_id}", Lobby)

    async def post_lobby(self, lobby: Lobby) -> Lobby:
        return await self._request(
            "POST", f"/api/Lobby", Lobby, json=lobby.model_dump_json()
        )

    async def put_lobby(self, lobby_id: int, lobby: Lobby) -> Lobby:
        return await self._request(
            "PUT", f"/api/Lobby/{lobby_id}", Lobby, json=lobby.model_dump_json()
        )

    async def delete_lobby(self, lobby_id: int) -> None:
        await self._request("DELETE", f"/api/Lobby/{lobby_id}", None)

    """
    Member API methods
    """

    async def post_member(self, member: Member) -> Member:
        return await self._request(
            "POST", "/api/Member", Member, json=member.model_dump_json()
        )

    async def put_member(self, member_id: int, lobby_id: int, member: Member) -> Member:
        return await self._request(
            "PUT",
            f"/api/Member/{lobby_id}/{member_id}",
            Member,
            json=member.model_dump_json(),
        )

    async def delete_member(self, member_id: int, lobby_id: int) -> None:
        await self._request("DELETE", f"/api/Member/{lobby_id}/{member_id}", None)

    """
    Game API methods
    """

    async def get_games(self) -> list[Game]:
        return await self._request("GET", "/api/Game/", Game)

    async def get_game(self, game_id: int) -> Game:
        return await self._request("GET", f"/api/Game/{game_id}", Game)

    async def post_game(self, game: Game) -> Game:
        return await self._request(
            "POST", "/api/Game", Game, json=game.model_dump_json()
        )

    async def put_game(self, game_id: int, game: Game) -> Game:
        return await self._request(
            "PUT", f"/api/Game/{game_id}", Game, json=game.model_dump_json()
        )

    async def delete_game(self, game_id: int) -> None:
        await self._request("DELETE", f"/api/Game/{game_id}", None)
