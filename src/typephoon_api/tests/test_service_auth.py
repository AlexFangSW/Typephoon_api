from ..services.auth import AuthService
import pytest
from .helper import (
    setting,
    sessionmaker,
    redis_conn,
    db_migration,
)


@pytest.mark.asyncio
async def test_auth_service_login_redirect(setting, sessionmaker, redis_conn):
    AuthService(setting, redis_conn, sessionmaker)
