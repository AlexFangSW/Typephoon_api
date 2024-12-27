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

    async def _send_loop(self):
        while True:
            msg = await self._queue.get()
            # check event and notify user
            ...

    async def _receive_loop(self):
        while True:
            ...

    async def start(self):
        self._send_task: Task = create_task(
            self._send_loop(),
            name=f"lobby_background_random-{self._user_info.id}-send")
        self._receive_task: Task = create_task(
            self._receive_loop(),
            name=f"lobby_background_random-{self._user_info.id}-receive")

    async def _before_end(self):
        ...

    async def stop(self):
        await self._before_end()
        self._send_task.cancel()
        self._receive_task.cancel()
        await self._websocket.close()
