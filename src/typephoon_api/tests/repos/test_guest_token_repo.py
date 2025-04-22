import pytest

from ...repositories.guest_token import GuestTokenRepo
from ..helper import *


@pytest.mark.asyncio
async def test_guest_token_repo_store(redis_conn: Redis, setting: Setting):
    dummy_token = "token"
    repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    key = await repo.store(dummy_token)

    ret: bytes = await redis_conn.get(key)
    assert ret
    assert ret.decode() == dummy_token


@pytest.mark.asyncio
async def test_guest_token_repo_get(redis_conn: Redis, setting: Setting):
    dummy_token = "token"
    repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    key = await repo.store(dummy_token)

    ret = await repo.get(key)
    assert ret
    assert ret == dummy_token
