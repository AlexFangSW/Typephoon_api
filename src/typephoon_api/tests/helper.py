from alembic import command
from alembic.config import Config
from pydantic_core import Url
import pytest
import pytest_asyncio
from os import getenv
from httpx import ASGITransport, AsyncClient
from asgi_lifespan import LifespanManager

from ..lib.server_setup import create_server
from ..types.setting import Setting

DSN = getenv("DSN", "postgresql://typephoon:123@localhost/typephoon")
API_PREFIX = "/api/v1"


@pytest.fixture
def db_migration_for_tests():
    config = Config()
    config.set_main_option("script_location", "migration")
    config.set_main_option("sqlalchemy.url", DSN)
    command.upgrade(config, "head")

    yield

    command.downgrade(config, "base")


def dummy_setting() -> Setting:
    with open("setting.json", "r") as f:
        setting = Setting.model_validate_json(f.read())

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

    return setting


@pytest_asyncio.fixture
async def client(db_migration_for_tests):
    setting = dummy_setting()
    app = create_server(setting)

    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        base_url = f"http://localhost:{setting.server.port}"
        async with AsyncClient(transport=transport,
                               base_url=base_url) as client:
            yield client
