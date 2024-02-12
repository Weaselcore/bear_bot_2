import aiohttp


class ClientSessionManager:
    def __init__(self):
        self._session = aiohttp.ClientSession()

    @property
    def session(self):
        return self._session


# async def main():
#     session_manager = ClientSessionManager()
#     await session_manager.create_session()

#     try:
#         async with session_manager._session.get('https://example.com') as response:
#             print(await response.text())
#     except aiohttp.ClientError as e:
#         print(f"An error occurred: {e}")
#     finally:
#         await session_manager.close_session()
