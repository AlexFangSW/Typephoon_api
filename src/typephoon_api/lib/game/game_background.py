from asyncio import Queue, Task, create_task
from logging import getLogger
from fastapi import WebSocket

from ...types.amqp import GameNotifyType

from ...types.log import TRACE

from .base import GameBGNotifyMsg

from ...types.common import GameUserInfo

logger = getLogger(__name__)


class GameBackground:
    """
    Background task for a single user
    """

    def __init__(
        self,
        websocket: WebSocket,
        user_info: GameUserInfo,
        send_queue: Queue[GameBGNotifyMsg],
    ) -> None:
        self._user_info = user_info
        self._queue: Queue[GameBGNotifyMsg] = Queue()
        self._send_queue = send_queue
        self._websocket = websocket

    @property
    def user_info(self) -> GameUserInfo:
        return self._user_info

    async def notifiy(self, msg: GameBGNotifyMsg):
        await self._queue.put(msg)

    async def _recive_loop(self):
        while True:
            msg = await self._queue.get()
            logger.log(TRACE, "recive message, msg: %s", msg)
            await self._websocket.send_bytes(msg.slim_dump_json().encode())

    async def _send_loop(self):
        while True:
            msg = await self._websocket.receive_bytes()
            data = GameBGNotifyMsg.model_validate_json(msg)
            if data.notify_type == GameNotifyType.KEY_STROKE:
                logger.log(TRACE, "send message")
                await self._send_queue.put(data)

    async def start(self):
        self._recive_task: Task = create_task(
            self._recive_loop(), name=f"game-background-recive-{self._user_info.id}"
        )
        self._send_task: Task = create_task(
            self._send_loop(), name=f"game-background-send-{self._user_info.id}"
        )

    async def stop(self, final_msg: GameBGNotifyMsg | None = None):
        try:
            if final_msg:
                await self._websocket.send_bytes(final_msg.slim_dump_json().encode())

            self._recive_task.cancel()
            self._send_task.cancel()
            await self._websocket.close()
        except Exception as ex:
            logger.warning("stop error: %s", str(ex))
