from asyncio import Queue, Task, create_task
from fastapi import WebSocket

from ...types.amqp import LobbyNotifyType

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

    @property
    def user_info(self) -> LobbyUserInfo:
        return self._user_info

    async def notifiy(self, msg: LobbyBGNotifyMsg):
        await self._queue.put(msg)

    async def _loop(self):
        while True:
            msg = await self._queue.get()
            await self._websocket.send_bytes(msg.slim_dump_json().encode())

    async def start(self):
        self._task: Task = create_task(
            self._loop(),
            name=f"lobby_background_random-{self._user_info.id}-send")

    async def stop(self):
        # send reconnect event to user
        msg = LobbyBGNotifyMsg(
            notify_type=LobbyNotifyType.RECONNECT).slim_dump_json().encode()
        await self._websocket.send_bytes(msg)

        self._task.cancel()
        await self._websocket.close()
