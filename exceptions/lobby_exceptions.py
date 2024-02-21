from discord import Thread, app_commands


class LobbyNotFound(Exception):
    """Occurs when server returns a 404 when querying for a lobby."""

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


class ThreadChannelNotFound(app_commands.AppCommandError):
    """Occurs when lobby history_thread_id is None"""
    pass


class LobbyChannelNotFound(app_commands.AppCommandError):
    """Occurs when lobby lobby_channel_id is None"""
    pass


class LobbyCreationError(Exception):
    def __init__(self, message: str):
        self.message = message

    def __str__(self) -> str:
        return self.message


class DeletedLobby(Exception):
    """Occurs when the server has deleted a lobby."""

    pass


class DeletedGame(Exception):
    pass


class MemberAlreadyInLobby(app_commands.AppCommandError):
    """Occurs when a member joins a lobby while already being in one."""

    def __init__(self, display_name: str, lobby_id: int, thread: Thread):
        self.message = f"{display_name}, you are already in another lobby with ID: {lobby_id}."
        self.thread = thread

    def __str__(self) -> str:
        return self.message
