from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql import select

from ...orm.user import User

from ...types.enums import UserType

from ...repositories.user import UserRepo

import pytest
from ..helper import *


@pytest.mark.asyncio
async def test_user_repo_token_upsert(
        sessionmaker: async_sessionmaker[AsyncSession]):
    dummy_token = "token"
    dummy_user_id = "user_id"
    dummy_username = "username"
    dummy_user_type = UserType.REGISTERED

    # ----------------------------
    # New User
    # ----------------------------
    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.token_upsert(id=dummy_user_id,
                                name=dummy_username,
                                refresh_token=dummy_token,
                                user_type=dummy_user_type)
        await session.commit()

    async with sessionmaker() as session:
        query = select(User).where(User.id == dummy_user_id)
        user = await session.scalar(query)
        assert user
        assert user.id == dummy_user_id
        assert user.name == dummy_username
        assert user.user_type == dummy_user_type
        assert user.refresh_token == dummy_token

    # ----------------------------
    # Old User
    # ----------------------------
    new_dummy_token = dummy_token + "123"

    async with sessionmaker() as session:
        repo = UserRepo(session)
        await repo.token_upsert(id=dummy_user_id,
                                name=dummy_username + "123",
                                refresh_token=new_dummy_token,
                                user_type=UserType.GUEST)
        await session.commit()

    async with sessionmaker() as session:
        query = select(User).where(User.id == dummy_user_id)
        user_updated = await session.scalar(query)
        assert user_updated
        assert user_updated.id == dummy_user_id
        assert user_updated.name == dummy_username
        assert user_updated.user_type == dummy_user_type
        assert user_updated.refresh_token == new_dummy_token
        assert user_updated.registered_at == user.registered_at
