from dataclasses import dataclass
from logging import getLogger

from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError

from ..lib.background_tasks.base import BGManager
from ..lib.background_tasks.game import GameBG, GameBGMsg, GameBGMsgEvent
from ..types.amqp import KeystrokeHeader, KeystrokeMsg
from ..types.setting import Setting
from .base import AbstractConsumer

logger = getLogger(__name__)


@dataclass(slots=True)
class LoadMsgRet:
    body: KeystrokeMsg
    skip: bool = False


class KeystrokeConsumer(AbstractConsumer):
    def __init__(
        self,
        setting: Setting,
        amqp_conn: AbstractRobustConnection,
        bg_manager: BGManager[GameBGMsg, GameBG],
    ) -> None:
        super().__init__(setting, amqp_conn)
        self._bg_manager = bg_manager

    def _load_message(self, amqp_msg: AbstractIncomingMessage) -> LoadMsgRet:
        result = LoadMsgRet(body=KeystrokeMsg.model_validate_json(amqp_msg.body))

        # headers = KeystrokeHeader.model_validate(amqp_msg.headers)
        # if headers.source == self._setting.server_name:
        #     result.skip = True

        return result

    async def _process(self, msg: KeystrokeMsg):
        bg_msg = GameBGMsg(
            game_id=msg.game_id,
            event=GameBGMsgEvent.KEY_STOKE,
            user_id=msg.user_id,
            word_index=msg.word_index,
            char_index=msg.char_index,
        )
        await self._bg_manager.broadcast(game_id=msg.game_id, msg=bg_msg)

    async def on_message(self, amqp_msg: AbstractIncomingMessage):
        logger.debug("on message")
        try:
            msg = self._load_message(amqp_msg)
            if msg.skip:
                await amqp_msg.ack()
                return
        except ValidationError:
            logger.warning("drop bad message")
            await amqp_msg.ack()
            return
        except:
            logger.exception("unknown error")
            await amqp_msg.nack()
            return

        try:
            await self._process(msg.body)
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

        self._queue = await self._channel.get_queue(
            self._setting.amqp.game_keystroke_queue
        )

    async def start(self):
        logger.info("start")
        self._consumer_tag = await self._queue.consume(self.on_message)

    async def stop(self):
        logger.info("stop")
        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
