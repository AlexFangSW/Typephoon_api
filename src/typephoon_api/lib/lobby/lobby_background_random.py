from asyncio import Queue, Task, create_task
from fastapi import WebSocket

from .base import LobbyBGNotifyMsg

from ...types.common import LobbyUserInfo


class LobbyBackground:
    """
    Background task for a single user
    """

    def __init__(self, websocket: WebSocket, user_info: LobbyUserInfo) -> None:
        self._user_info = user_info
        self._queue: Queue[LobbyBGNotifyMsg] = Queue()
        self._websocket = websocket

    async def notifiy(self, msg: LobbyBGNotifyMsg):
        await self._queue.put(msg)

    async def _send_loop(self):
        while True:
            msg = await self._queue.get()
            # check event and notify user
            ...

    async def start(self):
        self._task: Task = create_task(
            self._send_loop(),
            name=f"lobby_background_random-{self._user_info.id}-send")

    async def _before_end(self):
        ...

    async def stop(self):
        await self._before_end()
        self._task.cancel()
        await self._websocket.close()
