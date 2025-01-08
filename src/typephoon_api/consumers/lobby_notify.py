from collections import defaultdict
from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError

from ..lib.lobby.base import LobbyBGNotifyMsg

from ..lib.lobby.lobby_manager import LobbyBackgroundManager

from ..types.setting import Setting

from ..types.amqp import LobbyNotifyMsg, LobbyNotifyType
from .base import AbstractConsumer

logger = getLogger(__name__)


class LobbyNotifyConsumer(AbstractConsumer):
    """
    This consumer just consumes messages and pass them down.
    Logic should be in "LobbyBackground".
    """

    def __init__(
        self,
        setting: Setting,
        amqp_conn: AbstractRobustConnection,
        background_bucket: defaultdict[int, LobbyBackgroundManager],
    ) -> None:
        super().__init__(setting, amqp_conn)
        self._background_bucket = background_bucket

    def _load_message(self,
                      amqp_msg: AbstractIncomingMessage) -> LobbyNotifyMsg:
        return LobbyNotifyMsg.model_validate_json(amqp_msg.body)

    async def _process(self, msg: LobbyNotifyMsg):
        bg_notify_msg = LobbyBGNotifyMsg(notify_type=msg.notify_type,
                                         user_id=msg.user_id)

        if bg_notify_msg.notify_type == LobbyNotifyType.GAME_START:
            logger.debug("game started, game_id: %s", msg.game_id)
            await self._background_bucket[msg.game_id].stop(bg_notify_msg)
            self._background_bucket.pop(msg.game_id)

        else:
            await self._background_bucket[msg.game_id].broadcast(bg_notify_msg)

    async def _on_message(self, amqp_msg: AbstractIncomingMessage):
        logger.debug("on_message")
        try:
            msg = self._load_message(amqp_msg)
        except ValidationError:
            logger.warning("drop bad message")
            await amqp_msg.ack()
            return
        except:
            logger.exception("unknown error")
            await amqp_msg.nack()
            return

        try:
            await self._process(msg)
        except:
            logger.exception("process error !!")
            await amqp_msg.nack()
            return

        await amqp_msg.ack()
        logger.debug("ack message")

    async def prepare(self):
        logger.info("prepare")
        self._channel = await self._amqp_conn.channel()
        self._queue = await self._channel.get_queue(
            self._setting.amqp.lobby_notify_queue)

    async def start(self):
        logger.info("start")
        self._consumer_tag = await self._queue.consume(self._on_message)

    async def stop(self):
        logger.info("stop")
        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
