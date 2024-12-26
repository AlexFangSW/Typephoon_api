from asyncio import Queue, Task, create_task
from typing import Any
from fastapi import WebSocket

from ...types.common import LobbyUserInfo


class LobbyBackgroundRandom:
    """
    [Game mode: Random]
    Background task for a single user
    """

    def __init__(self, websocket: WebSocket, user_info: LobbyUserInfo) -> None:
        self._user_info = user_info
        self._queue = Queue()
        self._websocket = websocket
        pass

    async def notifiy(self, msg: Any):
        await self._queue.put(msg)

    async def prepare(self):
        ...

    async def _loop(self):
        while True:
            msg = await self._queue.get()
            ...

    async def start(self):
        self._task: Task = create_task(
            self._loop(), name=f"lobby_background_random-{self._user_info.id}")

    async def _before_end(self):
        ...

    async def stop(self):
        await self._before_end()
        self._task.cancel()
        await self._websocket.close()
