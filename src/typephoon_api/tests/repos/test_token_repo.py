from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...types.enums import UserType

from ...repositories.user import UserRepo
from ...repositories.token import TokenRepo
import pytest
from ..helper import *


@pytest.mark.asyncio
async def test_token_repo_set_refresh_token(
        sessionmaker: async_sessionmaker[AsyncSession]):

    dummy_token = "token"
    dummy_user_id = "user_id"
    dummy_username = "username"
    dummy_user_type = UserType.REGISTERED

    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.register(id=dummy_user_id,
                            name=dummy_username,
                            user_type=dummy_user_type)
        await session.commit()

    async with sessionmaker() as session:
        repo = TokenRepo(session)
        await repo.set_refresh_token(dummy_user_id, dummy_token)
        await session.commit()

    async with sessionmaker() as session:
        repo = UserRepo(session)
        user = await repo.get(dummy_user_id)
        assert user
        assert user.refresh_token == dummy_token
