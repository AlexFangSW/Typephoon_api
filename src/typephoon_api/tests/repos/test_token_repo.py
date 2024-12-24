from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...repositories.user import UserRepo
from ...repositories.token import TokenRepo
import pytest
from ..helper import *


@pytest.mark.asyncio
async def test_token_repo(sessionmaker: async_sessionmaker[AsyncSession]):

    dummy_token = "token"
    dummy_user_id = "user_id"
    dummy_username = "username"

    async with sessionmaker() as session:
        user_repo = UserRepo(session)
        token_repo = TokenRepo(session)

        # set
        await user_repo.register(id=dummy_user_id, name=dummy_username)
        await token_repo.set_refresh_token(dummy_user_id, dummy_token)

        user = await user_repo.get(dummy_user_id)
        assert user
        assert user.refresh_token == dummy_token

        # get
        refresh_token = await token_repo.get_refresh_token(dummy_user_id)
        assert refresh_token == dummy_token

        # delete
        await token_repo.remove_refresh_token(dummy_user_id)
        refresh_token = await token_repo.get_refresh_token(dummy_user_id)
        assert refresh_token is None
