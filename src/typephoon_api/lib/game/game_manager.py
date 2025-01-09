from __future__ import annotations
from asyncio import Queue, create_task
from logging import getLogger

from aio_pika import Message
from aio_pika.abc import AbstractRobustConnection, DeliveryMode
from pamqp.commands import Basic

from ...types.errors import PublishNotAcknowledged

from ...types.amqp import KeystrokeHeader

from ...types.setting import Setting

from .base import GameBGNotifyMsg

from .game_background import GameBackground

logger = getLogger(__name__)


async def init_game_background_manager(
    amqp_conn: AbstractRobustConnection,
    setting: Setting,
) -> GameBackgroundManager:

    manager = GameBackgroundManager(amqp_conn=amqp_conn, setting=setting)
    await manager.prepare()
    return manager


class GameBackgroundManager:

    def __init__(
        self,
        amqp_conn: AbstractRobustConnection,
        setting: Setting,
    ) -> None:
        self._background_tasks: dict[str, GameBackground] = {}
        self._send_queue: Queue[GameBGNotifyMsg] = Queue()
        self._amqp_conn = amqp_conn
        self._setting = setting

    @property
    def send_queue(self) -> Queue[GameBGNotifyMsg]:
        return self._send_queue

    async def _publish_loop(self):
        while True:
            msg = await self._send_queue.get()

            amqp_msg = Message(
                body=msg.model_dump_json().encode(),
                headers=KeystrokeHeader(source=self._setting.server_name).model_dump(),
                delivery_mode=DeliveryMode.PERSISTENT,
            )

            confirm = await self._exchange.publish(amqp_msg, routing_key="")
            if not isinstance(confirm, Basic.Ack):
                raise PublishNotAcknowledged("publish not acknowledged")

    async def add(self, bg: GameBackground):
        self._background_tasks[bg.user_info.id] = bg

    async def remove(self, user_id: str):
        bg = self._background_tasks.get(user_id)
        if not bg:
            return

        await bg.stop()
        self._background_tasks.pop(user_id)

    async def prepare(self):
        self._channel = await self._amqp_conn.channel()
        self._exchange = await self._channel.get_exchange(
            self._setting.amqp.game_keystroke_fanout_exchange
        )
        self._publish_task = create_task(
            self._publish_loop(), name=f"game-bg-manager-publish-loop"
        )

    async def broadcast(self, msg: GameBGNotifyMsg):
        for _, bg in self._background_tasks.items():
            await bg.notifiy(msg)

    async def stop(self, final_msg: GameBGNotifyMsg | None = None):
        self._publish_task.cancel()
        await self._channel.close()

        for _, bg in self._background_tasks.items():
            await bg.stop(final_msg)
