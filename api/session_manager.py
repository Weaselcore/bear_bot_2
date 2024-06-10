from aiohttp import ClientSession, TCPConnector


class ClientSessionManager:
    def __init__(self):
        self._session: ClientSession | None = None

    @property
    def session(self):
        if self._session == None:
            conn = TCPConnector(ssl=False)
            self._session = ClientSession(connector=conn)
        return self._session
    
    async def close(self) -> None:
        await self.session.close_session()