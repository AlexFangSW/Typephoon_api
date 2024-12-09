from contextlib import asynccontextmanager
from logging import getLogger
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext import asyncio
from ..api.health_check import router as health_check_router
from ..api.auth import router as auth_router
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from redis.asyncio import Redis

from ..types.setting import Setting

logger = getLogger(__name__)


class TypephoonServer(FastAPI):

    def __init__(self, setting: Setting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setting = setting

    async def prepare(self):
        # database
        # TODO: pool size and connectivity
        self._engine = create_async_engine(url=self._setting.db.async_dsn,
                                           isolation_level="READ COMMITTED")
        self._sessionmaker = async_sessionmaker(self._engine)

        # cache
        self._redis_conn = Redis(host=self._setting.redis.host,
                                 port=self._setting.redis.port,
                                 db=self._setting.redis.db)

    async def cleanup(self):
        await self._engine.dispose()
        await self._redis_conn.close()

    async def ready(self):
        # TODO: check connections
        ...

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        return self._sessionmaker

    @property
    def redis_conn(self) -> Redis:
        return self._redis_conn


@asynccontextmanager
async def lifespan(app: TypephoonServer):
    logger.info("lifespan startup")
    await app.prepare()

    yield

    logger.info("lifespan shutdown")
    await app.cleanup()


def create_server(setting: Setting) -> TypephoonServer:
    app = TypephoonServer(setting=setting, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=setting.cors.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1_router = APIRouter(prefix="/api/v1")
    v1_router.include_router(auth_router)

    app.include_router(health_check_router)
    app.include_router(v1_router)

    return app
