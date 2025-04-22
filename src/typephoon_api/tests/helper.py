from datetime import UTC, datetime

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ..lib.server_setup import create_server
from ..types.setting import Setting

API_PREFIX = "/api/v1"

tmp_now = datetime.now(UTC)
NOW = datetime(year=tmp_now.year, month=tmp_now.month, day=tmp_now.day, tzinfo=UTC)


@pytest.fixture
def setting() -> Setting:
    setting = Setting.from_file()
    return setting


@pytest.fixture
def db_migration(setting: Setting):
    config = Config()
    config.set_main_option("script_location", "migration")
    config.set_main_option("sqlalchemy.url", setting.db.dsn)
    command.upgrade(config, "head")

    yield

    command.downgrade(config, "base")


@pytest_asyncio.fixture
async def sessionmaker(db_migration, setting):
    engine = create_async_engine(
        url=setting.db.async_dsn,
        echo=setting.db.echo,
        pool_size=setting.db.pool_size,
        pool_pre_ping=True,
        pool_recycle=3600,
        isolation_level="READ COMMITTED",
    )
    sessionmaker = async_sessionmaker(engine)

    yield sessionmaker

    await engine.dispose()


@pytest_asyncio.fixture
async def redis_conn(setting: Setting):
    redis_conn = Redis(
        host=setting.redis.host, port=setting.redis.port, db=setting.redis.db
    )

    yield redis_conn

    await redis_conn.flushdb()
    await redis_conn.aclose()


@pytest_asyncio.fixture
async def client(db_migration, setting):
    app = create_server(setting)

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        base_url = f"http://localhost:{setting.server.port}"
        async with AsyncClient(transport=transport, base_url=base_url) as client:
            yield client
