from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from ..types.amqp import LobbyNotifyMsg
from .base import AbstractConsumer

logger = getLogger(__name__)


class LobbyCountdownConsumer(AbstractConsumer):

    def _load_message(self,
                      amqp_msg: AbstractIncomingMessage) -> LobbyNotifyMsg:
        return LobbyNotifyMsg.model_validate_json(amqp_msg.body)

    async def _process(self, msg: LobbyNotifyMsg):
        # start game and send game start event to specific team (notify message)
        ...

    async def on_message(self, amqp_msg: AbstractIncomingMessage):
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

        await self._channel.set_qos(
            prefetch_count=self._setting.amqp.prefetch_count)

        self._queue = await self._channel.get_queue(
            self._setting.amqp.lobby_countdown_queue)

    async def start(self):
        logger.info("start")

        self._consumer_tag = await self._queue.consume(self.on_message)

    async def stop(self):
        logger.info("stop")

        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
