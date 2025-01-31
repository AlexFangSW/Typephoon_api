from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game import GameRepo
from ..repositories.lobby_cache import LobbyCacheRepo
from ..repositories.game_cache import GameCacheRepo

from ..types.amqp import GameCleanupMsg

from ..types.setting import Setting
from .base import AbstractConsumer

logger = getLogger(__name__)


class GameCleanerConsumer(AbstractConsumer):

    def __init__(
        self,
        setting: Setting,
        amqp_conn: AbstractRobustConnection,
        sessionmaker: async_sessionmaker[AsyncSession],
        redis_conn: Redis,
    ) -> None:
        super().__init__(setting, amqp_conn)
        self._sessionmaker = sessionmaker
        self._redis_conn = redis_conn

    def _load_message(self, amqp_msg: AbstractIncomingMessage) -> GameCleanupMsg:
        return GameCleanupMsg.model_validate_json(amqp_msg.body)

    async def _process(self, msg: GameCleanupMsg):
        """
        set game status to FINISHED, and clear all cache
        """
        lobby_cache_repo = LobbyCacheRepo(
            redis_conn=self._redis_conn, setting=self._setting
        )
        game_cache_repo = GameCacheRepo(
            redis_conn=self._redis_conn, setting=self._setting
        )
        await lobby_cache_repo.clear_cache(msg.game_id)
        await game_cache_repo.clear_cache(msg.game_id)

        async with self._sessionmaker() as session:
            game_repo = GameRepo(session)
            await game_repo.set_finish(msg.game_id)
            await session.commit()

    async def on_message(self, amqp_msg: AbstractIncomingMessage):
        logger.debug("on message")
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

        self._queue = await self._channel.get_queue(
            self._setting.amqp.game_cleanup_queue
        )

    async def start(self):
        logger.info("start")
        self._consumer_tag = await self._queue.consume(self.on_message)

    async def stop(self):
        logger.info("stop")
        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
