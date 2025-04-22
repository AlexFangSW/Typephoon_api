from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
import time_machine
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...lib.oauth_providers.base import OAuthProviders, VerifyTokenRet
from ...lib.oauth_providers.google import GoogleOAuthProvider
from ...lib.token_generator import TokenGenerator
from ...lib.token_validator import TokenValidator
from ...lib.util import gen_user_id
from ...repositories.guest_token import GuestTokenRepo
from ...repositories.oauth_state import OAuthStateRepo
from ...repositories.token import TokenRepo
from ...repositories.user import UserRepo
from ...services.auth import AuthService
from ...types.enums import ErrorCode
from ...types.setting import Setting
from ..helper import *


@pytest.mark.asyncio
async def test_auth_service_login_redirect(
    setting: Setting, sessionmaker: async_sessionmaker[AsyncSession], redis_conn: Redis
):
    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"
    dummy_state = "state"
    dummy_code = "code"

    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    oauth_state_repo = OAuthStateRepo(setting, redis_conn)
    oauth_provider = GoogleOAuthProvider(setting, redis_conn, oauth_state_repo)
    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)

    service = AuthService(
        setting=setting,
        sessionmaker=sessionmaker,
        token_generator=token_generator,
        token_validator=token_validator,
        oauth_provider=oauth_provider,
        guest_token_repo=guest_token_repo,
    )

    # -------------------------------------------
    # failed
    # -------------------------------------------
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(ok=False)
    )

    ret = await service.login_redirect(dummy_state, dummy_code)
    assert not ret.ok

    # -------------------------------------------
    # success
    # -------------------------------------------
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(
            ok=True, user_id=dummy_user_id, username=dummy_username
        )
    )

    ret = await service.login_redirect(dummy_state, dummy_code)
    assert ret.ok
    assert ret.data
    assert ret.data.url == setting.front_end_endpoint
    assert ret.data.refresh_endpoint == setting.token.refresh_endpoint
    assert ret.data.username == dummy_username

    # check user refresh token
    async with sessionmaker() as session:
        repo = UserRepo(session)
        user = await repo.get(dummy_user_id)

    assert user
    assert user.refresh_token == ret.data.refresh_token


@pytest.mark.asyncio
async def test_auth_service_logout(
    setting: Setting, sessionmaker: async_sessionmaker[AsyncSession], redis_conn: Redis
):
    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"
    dummy_state = "state"
    dummy_code = "code"

    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    oauth_state_repo = OAuthStateRepo(setting, redis_conn)
    oauth_provider = GoogleOAuthProvider(setting, redis_conn, oauth_state_repo)
    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)

    service = AuthService(
        setting=setting,
        sessionmaker=sessionmaker,
        token_generator=token_generator,
        token_validator=token_validator,
        oauth_provider=oauth_provider,
        guest_token_repo=guest_token_repo,
    )

    # login
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(
            ok=True, user_id=dummy_user_id, username=dummy_username
        )
    )
    login_info = await service.login_redirect(dummy_state, dummy_code)
    assert login_info.data

    # logout
    ret = await service.logout(login_info.data.access_token)
    assert ret.ok
    # check that refresh token is removed
    async with sessionmaker() as session:
        repo = TokenRepo(session)
        refresh_token = await repo.get_refresh_token(dummy_user_id)
        assert refresh_token is None


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_auth_service_token_refresh(
    setting: Setting, sessionmaker: async_sessionmaker[AsyncSession], redis_conn: Redis
):
    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"
    dummy_state = "state"
    dummy_code = "code"

    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    oauth_state_repo = OAuthStateRepo(setting, redis_conn)
    oauth_provider = GoogleOAuthProvider(setting, redis_conn, oauth_state_repo)
    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)

    service = AuthService(
        setting=setting,
        sessionmaker=sessionmaker,
        token_generator=token_generator,
        token_validator=token_validator,
        oauth_provider=oauth_provider,
        guest_token_repo=guest_token_repo,
    )

    # login
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(
            ok=True, user_id=dummy_user_id, username=dummy_username
        )
    )
    login_info = await service.login_redirect(dummy_state, dummy_code)
    assert login_info.data

    # refresh (success)
    ret = await service.token_refresh(login_info.data.refresh_token)
    assert ret.ok

    # logout
    await service.logout(login_info.data.access_token)

    # refresh (fail, token missmatch)
    ret = await service.token_refresh(login_info.data.refresh_token)
    assert ret.ok is False
    assert ret.error
    assert ret.error.code == ErrorCode.REFRESH_TOKEN_MISSMATCH

    # refresh (fail, invalid token)
    with time_machine.travel(NOW + timedelta(seconds=setting.token.refresh_duration)):
        ret = await service.token_refresh(login_info.data.refresh_token)
        assert ret.ok is False
        assert ret.error
        assert ret.error.code == ErrorCode.INVALID_TOKEN
