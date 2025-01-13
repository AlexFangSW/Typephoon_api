from logging import getLogger
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection, DeliveryMode
from pamqp.commands import Basic
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from aio_pika import Message

from ..lib.background_tasks.lobby import LobbyBGMsgEvent

from ..repositories.game_cache import GameCacheRepo

from ..types.errors import PublishNotAcknowledged

from ..repositories.lobby_cache import LobbyCacheRepo

from ..repositories.game import GameRepo

from ..types.setting import Setting

from ..types.amqp import LobbyNotifyMsg
from .base import AbstractConsumer

logger = getLogger(__name__)


class LobbyCountdownConsumer(AbstractConsumer):

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

    def _load_message(self, amqp_msg: AbstractIncomingMessage) -> LobbyNotifyMsg:
        return LobbyNotifyMsg.model_validate_json(amqp_msg.body)

    async def _notify_all_users(self, game_id: int):
        notify_body = (
            LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.GAME_START, game_id=game_id)
            .slim_dump_json()
            .encode()
        )
        notify_msg = Message(notify_body, delivery_mode=DeliveryMode.PERSISTENT)
        confirm = await self._notify_exchange.publish(
            message=notify_msg, routing_key=""
        )
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("game start notify publish failed")

    async def _set_game_status(self, game_id: int) -> bool:
        async with self._sessionmaker() as session:
            game_repo = GameRepo(
                session=session, player_limit=self._setting.game.player_limit
            )

            # check current status
            game = await game_repo.get(game_id)
            if not game:
                logger.warning("game doesn't exist")
                return False
            if game.start_at is not None:
                logger.debug("game already started")
                return False

            await game_repo.start_game(game_id)
            await session.commit()

        return True

    async def _populate_game_cache(self, game_id: int):
        game_cache_repo = GameCacheRepo(
            redis_conn=self._redis_conn, setting=self._setting
        )
        lobby_cache_repo = LobbyCacheRepo(
            redis_conn=self._redis_conn, setting=self._setting
        )

        await game_cache_repo.populate_with_lobby_cache(
            game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
        )

    async def _process(self, msg: LobbyNotifyMsg):
        ok = await self._set_game_status(msg.game_id)
        if not ok:
            return
        await self._populate_game_cache(msg.game_id)
        await self._notify_all_users(msg.game_id)

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

        # lobby countdown
        self._channel = await self._amqp_conn.channel()
        await self._channel.set_qos(prefetch_count=self._setting.amqp.prefetch_count)
        self._queue = await self._channel.get_queue(
            self._setting.amqp.lobby_countdown_queue
        )

        # default exchange
        self._default_publish_channel = await self._amqp_conn.channel()
        self._default_exchange = self._default_publish_channel.default_exchange

        # notify fanout exchange
        self._notify_publish_channel = await self._amqp_conn.channel()
        self._notify_exchange = await self._notify_publish_channel.get_exchange(
            self._setting.amqp.lobby_notify_fanout_exchange
        )

    async def start(self):
        logger.info("start")
        self._consumer_tag = await self._queue.consume(self.on_message)

    async def stop(self):
        logger.info("stop")

        await self._queue.cancel(self._consumer_tag)
        await self._channel.close()
        await self._notify_publish_channel.close()
        await self._default_publish_channel.close()
