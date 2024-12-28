from asyncio import timeout
from collections import defaultdict
from logging import getLogger
from aio_pika import connect_robust
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from .amqp_manager import AMQPManager

from ..types.errors import AMQPNotReady

from .lobby.lobby_manager import LobbyBackgroundManager

from ..types.setting import Setting

logger = getLogger(__name__)


class TypephoonServer(FastAPI):

    def __init__(self, setting: Setting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setting = setting

    async def prepare(self):
        # database
        self._engine = create_async_engine(url=self._setting.db.async_dsn,
                                           echo=self._setting.db.echo,
                                           pool_size=self._setting.db.pool_size,
                                           pool_pre_ping=True,
                                           pool_recycle=3600,
                                           isolation_level="READ COMMITTED")
        self._sessionmaker = async_sessionmaker(self._engine)

        # cache (redis)
        self._redis_conn = Redis(host=self._setting.redis.host,
                                 port=self._setting.redis.port,
                                 db=self._setting.redis.db)

        # amqp
        self._amqp_conn = await connect_robust(
            host=self._setting.amqp.host,
            login=self._setting.amqp.user,
            password=self._setting.amqp.password,
            virtualhost=self._setting.amqp.vhost,
            client_properties={'connection_name': 'typephoon'})

        await AMQPManager(setting=self._setting,
                          amqp_conn=self._amqp_conn).setup()

        self._default_channel = await self._amqp_conn.channel()
        self._notify_channel = await self._amqp_conn.channel()
        self._default_exchange = self._default_channel.default_exchange
        self._notify_exchange = await self._notify_channel.get_exchange(
            self._setting.amqp.lobby_random_notify_fanout_exchange)

        # ------- [Game mode: Random] --------
        # lobby background tasks
        # - key: game_id
        self._lobby_bucket_random: defaultdict[
            str, LobbyBackgroundManager] = defaultdict()

        # TODO
        # lobby countdown consumer

        # lobby notify consumer

    async def cleanup(self):
        for team_id, lobby_manager in self._lobby_bucket_random.items():
            logger.debug("cleaning lobby: %s", team_id)
            await lobby_manager.stop()

        await self._engine.dispose()
        await self._redis_conn.aclose()
        await self._default_channel.close()
        await self._notify_channel.close()
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
    def lobby_bucket_random(self) -> defaultdict[str, LobbyBackgroundManager]:
        return self._lobby_bucket_random
