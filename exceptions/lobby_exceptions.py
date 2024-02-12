class LobbyNotFound(Exception):
    def __init__(self, lobby_id: int):
        self.message = f"Lobby with {lobby_id} not found."

    def __str__(self) -> str:
        return self.message
    

class LobbyNotFoundByOwnerId(Exception):
    pass


class MemberNotFound(Exception):
    def __init__(self, member_id: int):
        self.message = f"Member with {member_id} not found"

    def __str__(self) -> str:
        return self.message


class GuildNotFound(Exception):
    def __init__(self, guild_id: int):
        self.message = f"Guild with {guild_id} not found"

    def __str__(self) -> str:
        return self.message


class LobbyChannelNotFound(Exception):
    def __init__(self, lobby_channel_id: int):
        self.message = f"Lobby channel with {lobby_channel_id} not found"

    def __str__(self) -> str:
        return self.message


class LobbyCreationError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message
    

class DeletedLobby(Exception):
    """Exception raised for empty JSON response."""
    pass

class DeletedGame(Exception):
    pass
