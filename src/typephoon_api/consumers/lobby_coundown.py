from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError
from redis.asyncio import Redis, lock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game_cache import GameCacheRepo

from ..orm.game import GameStatus

from ..repositories.game import GameRepo

from ..types.setting import Setting

from ..types.amqp import LobbyNotifyMsg
from .base import AbstractConsumer

logger = getLogger(__name__)


class LobbyCountdownConsumer(AbstractConsumer):

    def __init__(self, setting: Setting, amqp_conn: AbstractRobustConnection,
                 sessionmaker: async_sessionmaker[AsyncSession],
                 redis_conn: Redis) -> None:
        super().__init__(setting, amqp_conn)
        self._sessionmaker = sessionmaker
        self._redis_conn = redis_conn

    def _load_message(self,
                      amqp_msg: AbstractIncomingMessage) -> LobbyNotifyMsg:
        return LobbyNotifyMsg.model_validate_json(amqp_msg.body)

    async def _process(self, msg: LobbyNotifyMsg):
        """
        [Start game]
        - Set game status to IN_GAME
        - Set game start time
        - Update game cache expiration --> 10 min ?
        - Start game start countdown (5s)
            - "game.start.wait" queue -- 5s --> "game.start" queue
            - Game start ts in cache for countdown pooling

        [Send event] 
        - Notify game start
            - {"game_id": xxx}
            - Frontend redirects users to gaming page
        """

        async with self._sessionmaker() as session:
            game_repo = GameRepo(session)
            game = await game_repo.start_game(msg.game_id)

            game_cache_repo = GameCacheRepo(redis_conn=self._redis_conn,
                                            setting=self._setting)
            ...

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
