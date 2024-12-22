from datetime import UTC, datetime, timedelta
import jwt
from jwt.exceptions import ExpiredSignatureError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ...repositories.user import UserRepo

from ...types.setting import Setting
from ...lib.util import gen_user_id, get_state_key
from ...services.auth import AuthService, VerifyGoogleTokenRet
import pytest
from unittest.mock import AsyncMock
import time_machine
from ..helper import *


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_auth_service_login_redirect(
        setting: Setting, sessionmaker: async_sessionmaker[AsyncSession],
        redis_conn: Redis):
    """
    Test if token generation and user register works
    """

    dummy_token = "token"
    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id)
    dummy_username = "username"
    dummy_state = "state"
    dummy_code = "code"
    dummy_state_key = get_state_key(dummy_state)

    service = AuthService(setting, redis_conn, sessionmaker)

    # mock access to google
    service._exchange_code_for_token = AsyncMock(return_value=dummy_token)
    service._verify_google_token = AsyncMock(return_value=VerifyGoogleTokenRet(
        ok=True, user_id=dummy_google_user_id, username=dummy_username))

    # -------------------------------------------
    # state not found
    # -------------------------------------------
    ret = await service.login_redirect(dummy_state, dummy_code)
    assert not ret.ok
    assert ret.error_redirect_url == setting.error_redirect

    # -------------------------------------------
    # check token
    # -------------------------------------------
    await redis_conn.set(dummy_state_key, 1)
    ret = await service.login_redirect(dummy_state, dummy_code)
    assert ret.ok
    assert ret.data
    assert ret.data.url == setting.front_end_endpoint
    assert ret.data.refresh_endpoint == setting.token.refresh_endpoint

    # check token params
    decoded_access_token = jwt.decode(jwt=ret.data.access_token,
                                      key=setting.token.public_key,
                                      options={
                                          "verify_signature": True,
                                          "verify_aud": False,
                                          "verify_iss": False,
                                      },
                                      algorithms=["RS256"])
    assert decoded_access_token['sub'] == dummy_user_id
    assert decoded_access_token['name'] == dummy_username
    iat = datetime.fromtimestamp(decoded_access_token['iat'], UTC)
    exp = datetime.fromtimestamp(decoded_access_token['exp'], UTC)
    nbf = datetime.fromtimestamp(decoded_access_token['nbf'], UTC)
    assert iat == NOW
    assert exp == NOW + timedelta(seconds=setting.token.access_duration)
    assert nbf == NOW - timedelta(seconds=1)

    # in range
    with time_machine.travel(NOW + timedelta(
            seconds=setting.token.access_duration - 1)):
        jwt.decode(jwt=ret.data.access_token,
                   key=setting.token.public_key,
                   options={
                       "verify_signature": True,
                       "verify_aud": False,
                       "verify_iss": False,
                   },
                   algorithms=["RS256"])

    # expired
    with time_machine.travel(NOW +
                             timedelta(seconds=setting.token.access_duration)):
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(jwt=ret.data.access_token,
                       key=setting.token.public_key,
                       options={
                           "verify_signature": True,
                           "verify_aud": False,
                           "verify_iss": False,
                       },
                       algorithms=["RS256"])

    decoded_refresh_token = jwt.decode(jwt=ret.data.refresh_token,
                                       key=setting.token.public_key,
                                       options={
                                           "verify_signature": True,
                                           "verify_aud": False,
                                           "verify_iss": False,
                                       },
                                       algorithms=["RS256"])
    assert decoded_refresh_token['sub'] == dummy_user_id
    assert decoded_refresh_token['name'] == dummy_username
    iat = datetime.fromtimestamp(decoded_refresh_token['iat'], UTC)
    exp = datetime.fromtimestamp(decoded_refresh_token['exp'], UTC)
    nbf = datetime.fromtimestamp(decoded_refresh_token['nbf'], UTC)
    assert iat == NOW
    assert exp == NOW + timedelta(seconds=setting.token.refresh_duration)
    assert nbf == NOW - timedelta(seconds=1)

    # in range
    with time_machine.travel(NOW + timedelta(
            seconds=setting.token.refresh_duration - 1)):
        jwt.decode(jwt=ret.data.refresh_token,
                   key=setting.token.public_key,
                   options={
                       "verify_signature": True,
                       "verify_aud": False,
                       "verify_iss": False,
                   },
                   algorithms=["RS256"])

    # expired
    with time_machine.travel(NOW +
                             timedelta(seconds=setting.token.refresh_duration)):
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(jwt=ret.data.refresh_token,
                       key=setting.token.public_key,
                       options={
                           "verify_signature": True,
                           "verify_aud": False,
                           "verify_iss": False,
                       },
                       algorithms=["RS256"])

    # check user refresh token
    async with sessionmaker() as session:
        repo = UserRepo(session)
        user = await repo.get(dummy_user_id)

    assert user
    assert user.refresh_token == ret.data.refresh_token
