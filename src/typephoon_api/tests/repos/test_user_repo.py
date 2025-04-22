import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...orm.user import User
from ...repositories.user import UserRepo
from ..helper import *


@pytest.mark.asyncio
async def test_user_repo_create(sessionmaker: async_sessionmaker[AsyncSession]):
    dummy_user_id = "user_id"
    dummy_username = "username"

    # ----------------
    # new user
    # ----------------
    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.register(id=dummy_user_id, name=dummy_username)
        await session.commit()

    # check
    async with sessionmaker() as session:
        new_user = await session.get_one(User, dummy_user_id)
        assert new_user.id == dummy_user_id
        assert new_user.name == dummy_username
        assert new_user.refresh_token is None

    # ----------------
    # again
    # ----------------
    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.register(id=dummy_user_id, name=dummy_username)
        await session.commit()

    # check
    async with sessionmaker() as session:
        user = await session.get_one(User, dummy_user_id)
        assert user.id == new_user.id
        assert user.name == new_user.name
        assert user.refresh_token == new_user.refresh_token
        assert user.registered_at == new_user.registered_at


@pytest.mark.asyncio
async def test_user_repo_get(sessionmaker: async_sessionmaker[AsyncSession]):
    dummy_user_id = "user_id"
    dummy_username = "username"

    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.register(id=dummy_user_id, name=dummy_username)
        await session.commit()

    async with sessionmaker() as session:
        repo = UserRepo(session)
        user = await repo.get(dummy_user_id)
        assert user
        assert user.id == dummy_user_id
        assert user.name == dummy_username
        assert user.refresh_token is None
