from asyncio import Queue, Task, create_task, Event
from logging import getLogger
from fastapi import WebSocket

from ...types.amqp import LobbyNotifyType

from .base import LobbyBGNotifyMsg

from ...types.common import LobbyUserInfo

logger = getLogger(__name__)


class LobbyBackground:
    """
    Background task for a single user
    """

    def __init__(self, websocket: WebSocket, user_info: LobbyUserInfo) -> None:
        self._user_info = user_info
        self._queue: Queue[LobbyBGNotifyMsg] = Queue()
        self._websocket = websocket
        self._end_event = Event()

    @property
    def user_info(self) -> LobbyUserInfo:
        return self._user_info

    async def notifiy(self, msg: LobbyBGNotifyMsg):
        await self._queue.put(msg)

    async def _loop(self):
        while True:
            msg = await self._queue.get()
            await self._websocket.send_bytes(msg.slim_dump_json().encode())

            if msg.notify_type == LobbyNotifyType.GAME_START:
                self._end_event.set()
                break

    async def start(self):
        self._task: Task = create_task(
            self._loop(),
            name=f"lobby_background_random-{self._user_info.id}-send")

    async def stop(self, reconnect: bool = False, now: bool = False):
        if not now:
            await self._end_event.wait()
        else:
            self._task.cancel()

        # send reconnect event to user
        if reconnect:
            msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.RECONNECT
                                  ).slim_dump_json().encode()
            await self._websocket.send_bytes(msg)

        await self._websocket.close()
