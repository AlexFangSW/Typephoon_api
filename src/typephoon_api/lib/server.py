from logging import getLogger
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from ..schemas.setting import Setting

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

    async def cleanup(self):
        await self._engine.dispose()
        await self._redis_conn.close()

    async def ready(self) -> bool:
        try:
            # database
            async with self._sessionmaker() as session:
                await session.execute(text("SELECT 1"))

            # redis
            await self._redis_conn.ping()

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
