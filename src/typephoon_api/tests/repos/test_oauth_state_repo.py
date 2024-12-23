from ...repositories.oauth_state import OAuthStateRepo

import pytest
from ..helper import *


@pytest.mark.asyncio
async def test_oauth_state_repo(redis_conn: Redis, setting: Setting):
    repo = OAuthStateRepo(setting=setting, redis_conn=redis_conn)

    ret = await repo.state_exist("doesn't exist")
    assert ret is False

    state = await repo.set_state()
    ret = await repo.state_exist(state)
    assert ret

    ret = await repo.state_exist(state)
    assert ret is False
