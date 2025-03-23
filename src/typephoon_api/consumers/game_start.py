from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError
from ..lib.background_tasks.game import GameBG, GameBGMsg, GameBGMsgEvent
from ..lib.background_tasks.base import BGManager
from ..types.setting import Setting
from ..types.amqp import GameStartMsg
from .base import AbstractConsumer

logger = getLogger(__name__)


class GameStartConsumer(AbstractConsumer):
    def __init__(
        self,
        setting: Setting,
        amqp_conn: AbstractRobustConnection,
        bg_manager: BGManager[GameBGMsg, GameBG],
    ) -> None:
        super().__init__(setting, amqp_conn)
        self._bg_manager = bg_manager

    def _load_message(self, amqp_msg: AbstractIncomingMessage) -> GameStartMsg:
        return GameStartMsg.model_validate_json(amqp_msg.body)

    async def _process(self, msg: GameStartMsg):
        # notify all users
        bg_msg = GameBGMsg(event=GameBGMsgEvent.START, game_id=msg.game_id)
        await self._bg_manager.broadcast(game_id=msg.game_id, msg=bg_msg)

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
        await self._channel.set_qos(prefetch_count=self._setting.amqp.prefetch_count)
        self._queue = await self._channel.get_queue(self._setting.amqp.game_start_queue)

    async def start(self):
        logger.info("start")
        self._consumer_tag = await self._queue.consume(self.on_message)

    async def stop(self):
        logger.info("stop")

        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
