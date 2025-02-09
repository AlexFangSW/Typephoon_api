from asyncio import timeout
from logging import getLogger
from aio_pika import connect_robust
from aio_pika.abc import AbstractExchange
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from ..consumers.game_cleaner import GameCleanerConsumer

from .background_tasks.lobby import LobbyBG, LobbyBGMsg, LobbyBGMsgEvent

from .background_tasks.base import BGManager
from .background_tasks.game import GameBG, GameBGMsg, GameBGMsgEvent

from ..consumers.keystroke import KeystrokeConsumer

from ..consumers.lobby_notify import LobbyNotifyConsumer

from ..consumers.lobby_coundown import LobbyCountdownConsumer

from .amqp_manager import AMQPManager

from ..types.errors import AMQPNotReady
from ..types.setting import Setting

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

        updated_queue_names = await AMQPManager(
            setting=self._setting, amqp_conn=self._amqp_conn
        ).setup()

        # update queue names
        self._setting.amqp.lobby_multi_countdown_wait_queue = (
            updated_queue_names.lobby_multi_wait
        )
        self._setting.amqp.game_cleanup_wait_queue = (
            updated_queue_names.game_cleanup_wait
        )

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
        self._lobby_bg_manager = BGManager[LobbyBGMsg, LobbyBG](
            msg_type=LobbyBGMsg, bg_type=LobbyBG, setting=self._setting
        )
        await self._lobby_bg_manager.start()

        # in game background tasks (key: game_id)
        self._game_bg_manager = BGManager[GameBGMsg, GameBG](
            msg_type=GameBGMsg, bg_type=GameBG, setting=self._setting
        )
        await self._game_bg_manager.start()

        # consumers
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
            bg_manager=self._lobby_bg_manager,
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

        self._game_cleaner_consumer = GameCleanerConsumer(
            setting=self._setting,
            amqp_conn=self._amqp_conn,
            redis_conn=self._redis_conn,
            sessionmaker=self._sessionmaker,
        )
        await self._game_cleaner_consumer.prepare()
        await self._game_cleaner_consumer.start()

    async def cleanup(self):
        await self._lobby_notify_consumer.stop()
        await self._lobby_countdown_consumer.stop()
        await self._keystroke_consumer.stop()
        await self._game_cleaner_consumer.stop()

        await self._lobby_bg_manager.stop()
        await self._game_bg_manager.stop()

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
    def lobby_bg_manager(self) -> BGManager[LobbyBGMsg, LobbyBG]:
        return self._lobby_bg_manager

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
