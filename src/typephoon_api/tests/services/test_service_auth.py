from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...oauth_providers.base import VerifyTokenRet

from ...oauth_providers.google import GoogleOAuthProvider

from ...lib.token_generator import TokenGenerator

from ...repositories.oauth_state import OAuthStateRepo

from ...types.enums import OAuthProviders

from ...repositories.user import UserRepo

from ...types.setting import Setting
from ...lib.util import gen_user_id
from ...services.auth import AuthService
import pytest
from unittest.mock import AsyncMock
from ..helper import *


@pytest.mark.asyncio
async def test_auth_service_login_redirect(
        setting: Setting, sessionmaker: async_sessionmaker[AsyncSession],
        redis_conn: Redis):

    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"
    dummy_state = "state"
    dummy_code = "code"

    token_generator = TokenGenerator(setting)
    oauth_state_repo = OAuthStateRepo(setting, redis_conn)
    oauth_provider = GoogleOAuthProvider(setting, redis_conn, oauth_state_repo)

    service = AuthService(setting=setting,
                          sessionmaker=sessionmaker,
                          token_generator=token_generator,
                          oauth_provider=oauth_provider)

    # -------------------------------------------
    # failed
    # -------------------------------------------
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(ok=False))

    ret = await service.login_redirect(dummy_state, dummy_code)
    assert not ret.ok
    assert ret.error_redirect_url == setting.error_redirect

    # -------------------------------------------
    # seccess
    # -------------------------------------------
    oauth_provider.handle_authorization_response = AsyncMock(
        return_value=VerifyTokenRet(
            ok=True, user_id=dummy_user_id, username=dummy_username))

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
