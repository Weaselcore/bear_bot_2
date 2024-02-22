from aiohttp import ClientSession


class ClientSessionManager:
    def __init__(self):
        self._session: ClientSession | None = None

    @property
    def session(self):
        if self._session == None: 
            self._session = ClientSession()
        return self._session
    
    async def close(self) -> None:
        await self.session.close_session()