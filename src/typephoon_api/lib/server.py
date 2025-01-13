from asyncio import timeout
from collections import defaultdict
from logging import getLogger
from aio_pika import connect_robust
from aio_pika.abc import AbstractExchange
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from .background_tasks.base import BGManager
from .background_tasks.game import GameBG, GameBGMsg, GameBGMsgEvent

from ..consumers.keystroke import KeystrokeConsumer

from .lobby.base import LobbyBGNotifyMsg
from ..types.amqp import LobbyNotifyType

from ..consumers.lobby_notify import LobbyNotifyConsumer

from ..consumers.lobby_coundown import LobbyCountdownConsumer

from .amqp_manager import AMQPManager

from ..types.errors import AMQPNotReady

from .lobby.lobby_manager import LobbyBackgroundManager

from ..types.setting import Setting
from ..types import setting

logger = getLogger(__name__)


class TypephoonServer(FastAPI):

    def __init__(self, setting: Setting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setting = setting

    async def prepare(self):
        # database
        self._engine = create_async_engine(
            url=self._setting.db.async_dsn,
            echo=self._setting.db.echo,
            pool_size=self._setting.db.pool_size,
            pool_pre_ping=True,
            pool_recycle=3600,
            isolation_level="READ COMMITTED",
        )
        self._sessionmaker = async_sessionmaker(self._engine)

        # cache (redis)
        self._redis_conn = Redis(
            host=self._setting.redis.host,
            port=self._setting.redis.port,
            db=self._setting.redis.db,
        )

        # amqp
        self._amqp_conn = await connect_robust(
            host=self._setting.amqp.host,
            login=self._setting.amqp.user,
            password=self._setting.amqp.password,
            virtualhost=self._setting.amqp.vhost,
            client_properties={"connection_name": "typephoon"},
        )

        await AMQPManager(setting=self._setting, amqp_conn=self._amqp_conn).setup()

        self._default_channel = await self._amqp_conn.channel()
        self._notify_channel = await self._amqp_conn.channel()
        self._keystroke_channel = await self._amqp_conn.channel()

        self._default_exchange = self._default_channel.default_exchange
        self._notify_exchange = await self._notify_channel.get_exchange(
            self._setting.amqp.lobby_notify_fanout_exchange
        )
        self._keystroke_exchange = await self._keystroke_channel.get_exchange(
            self._setting.amqp.game_keystroke_fanout_exchange
        )

        # lobby background tasks (key: game_id)
        self._lobby_background_bucket: defaultdict[int, LobbyBackgroundManager] = (
            defaultdict(LobbyBackgroundManager)
        )

        # in game background tasks
        self._game_bg_manager = BGManager[GameBGMsg, GameBG](
            msg_type=GameBGMsg, bg_type=GameBG, setting=self._setting
        )
        await self._game_bg_manager.start()

        self._lobby_countdown_consumer = LobbyCountdownConsumer(
            setting=self._setting,
            amqp_conn=self._amqp_conn,
            sessionmaker=self._sessionmaker,
            redis_conn=self._redis_conn,
        )
        await self._lobby_countdown_consumer.prepare()
        await self._lobby_countdown_consumer.start()

        self._lobby_notify_consumer = LobbyNotifyConsumer(
            setting=self._setting,
            amqp_conn=self._amqp_conn,
            background_bucket=self._lobby_background_bucket,
        )
        await self._lobby_notify_consumer.prepare()
        await self._lobby_notify_consumer.start()

        self._keystroke_consumer = KeystrokeConsumer(
            setting=self._setting,
            amqp_conn=self._amqp_conn,
            bg_manager=self._game_bg_manager,
        )
        await self._keystroke_consumer.prepare()
        await self._keystroke_consumer.start()

    async def cleanup(self):
        await self._lobby_notify_consumer.stop()
        await self._lobby_countdown_consumer.stop()
        await self._keystroke_consumer.stop()

        for game_id, manager in self._lobby_background_bucket.items():
            logger.debug("cleaning lobby: %s", game_id)
            msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.RECONNECT)
            await manager.stop(msg)

        await self._game_bg_manager.stop(GameBGMsg(event=GameBGMsgEvent.RECONNECT))

        await self._engine.dispose()
        await self._redis_conn.aclose()
        await self._default_channel.close()
        await self._notify_channel.close()
        await self._keystroke_channel.close()
        await self._amqp_conn.close()

    async def ready(self) -> bool:
        try:
            # database
            async with self._sessionmaker() as session:
                await session.execute(text("SELECT 1"))

            # redis
            await self._redis_conn.ping()

            # amqp
            try:
                async with timeout(0.1):
                    await self._amqp_conn.ready()
            except TimeoutError:
                raise AMQPNotReady("amqp_conn not ready")

        except Exception as ex:
            logger.warning("failed 'ready' check, error: %s", str(ex))
            return False

        else:
            return True

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        return self._sessionmaker

    @property
    def redis_conn(self) -> Redis:
        return self._redis_conn

    @property
    def setting(self) -> Setting:
        return self._setting

    @property
    def lobby_background_bucket(self) -> defaultdict[int, LobbyBackgroundManager]:
        return self._lobby_background_bucket

    @property
    def amqp_default_exchange(self) -> AbstractExchange:
        return self._default_exchange

    @property
    def amqp_notify_exchange(self) -> AbstractExchange:
        return self._notify_exchange

    @property
    def amqp_keystroke_exchange(self) -> AbstractExchange:
        return self._keystroke_exchange

    @property
    def game_bg_manager(self) -> BGManager[GameBGMsg, GameBG]:
        return self._game_bg_manager
