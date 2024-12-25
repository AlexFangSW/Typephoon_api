from datetime import UTC, datetime
from alembic import command
from alembic.config import Config
from pydantic_core import Url
import pytest
import pytest_asyncio
from os import getenv
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ..lib.server_setup import create_server
from ..types.setting import Setting

DSN = getenv("DSN", "postgresql://typephoon:123@localhost/typephoon")

REDIS_HOST = getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(getenv("REDIS_PORT", 6379))
REDIS_DB = int(getenv("REDIS_DB", 0))

API_PREFIX = "/api/v1"

tmp_now = datetime.now(UTC)
NOW = datetime(year=tmp_now.year,
               month=tmp_now.month,
               day=tmp_now.day,
               tzinfo=UTC)


@pytest.fixture
def db_migration():
    config = Config()
    config.set_main_option("script_location", "migration")
    config.set_main_option("sqlalchemy.url", DSN)
    command.upgrade(config, "head")

    yield

    command.downgrade(config, "base")


@pytest.fixture
def setting() -> Setting:
    setting = Setting.from_file()

    # DATABASE
    dsn = Url(DSN)
    if dsn.host:
        setting.db.host = dsn.host
    if dsn.port:
        setting.db.port = dsn.port
    if dsn.path:
        setting.db.db = dsn.path.lstrip("/")
    if dsn.username:
        setting.db.username = dsn.username
    if dsn.password:
        setting.db.password = dsn.password

    # REDIS
    setting.redis.host = REDIS_HOST
    setting.redis.port = REDIS_PORT
    setting.redis.db = REDIS_DB

    return setting


@pytest_asyncio.fixture
async def sessionmaker(db_migration, setting):
    engine = create_async_engine(url=setting.db.async_dsn,
                                 echo=setting.db.echo,
                                 pool_size=setting.db.pool_size,
                                 pool_pre_ping=True,
                                 pool_recycle=3600,
                                 isolation_level="READ COMMITTED")
    sessionmaker = async_sessionmaker(engine)

    yield sessionmaker

    await engine.dispose()


@pytest_asyncio.fixture
async def redis_conn(setting: Setting):
    redis_conn = Redis(host=setting.redis.host,
                       port=setting.redis.port,
                       db=setting.redis.db)

    yield redis_conn

    await redis_conn.flushdb()
    await redis_conn.aclose()


@pytest_asyncio.fixture
async def client(db_migration, setting):
    app = create_server(setting)

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        base_url = f"http://localhost:{setting.server.port}"
        async with AsyncClient(transport=transport,
                               base_url=base_url) as client:
            yield client
