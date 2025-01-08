from asyncio import Queue, Task, create_task, Event
from logging import getLogger
from fastapi import WebSocket

from .base import GameBGNotifyMsg

from ...types.common import GameUserInfo

logger = getLogger(__name__)


class GameBackground:
    """
    Background task for a single user
    """

    def __init__(self, websocket: WebSocket, user_info: GameUserInfo) -> None:
        self._user_info = user_info
        self._queue: Queue[GameBGNotifyMsg] = Queue()
        self._websocket = websocket
        self._end_event = Event()

    @property
    def user_info(self) -> GameUserInfo:
        return self._user_info

    async def notifiy(self, msg: GameBGNotifyMsg):
        await self._queue.put(msg)

    async def _loop(self):
        while True:
            msg = await self._queue.get()
            await self._websocket.send_bytes(msg.slim_dump_json().encode())

    async def start(self):
        self._task: Task = create_task(
            self._loop(), name=f"game_background-{self._user_info.id}")

    async def stop(self, final_msg: GameBGNotifyMsg | None = None):
        if final_msg:
            await self._websocket.send_bytes(
                final_msg.slim_dump_json().encode())

        self._task.cancel()
        await self._websocket.close()
