from typing import Protocol, List

from discord.ui import View


class BattleShipGameButton(Protocol):
    disabled: bool
    ...


class BattleShipGameGridView(Protocol):
    lobby_id: int
    children: List[BattleShipGameButton]
    ...

    def set_loser_board(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def enable(self) -> None:
        ...

    def disable(self) -> None:
        ...


class DoneButton(Protocol):

    async def update(self) -> None:
        ...

    def add_message(self) -> None:
        ...


class BattleShipStatusView(Protocol):

    def update(self) -> None: ...

    def stop(self) -> None: ...


class BattleshipSetupGridView(Protocol):

    async def update(self) -> None: ...

    def stop(self) -> None: ...


class BattleShipGameModel(Protocol):
    ...


class Client(Protocol):
    battleship_games: dict[int, BattleShipGameModel]

    def dispatch(self, event: str, lobby_id: int) -> None: ...


class Message(Protocol):
    ...


class Channel(Protocol):

    async def send(self, content: str | None = None, view: View | None = None) -> Message:
        ...
