from datetime import timedelta
from jwt.exceptions import ExpiredSignatureError
import pytest
import jwt
import time_machine

from ...lib.oauth_providers.base import OAuthProviders

from ...lib.util import gen_user_id

from ...lib.token_generator import TokenGenerator
from ..helper import *


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_token_generator(setting: Setting):
    token_generator = TokenGenerator(setting=setting)

    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"

    ret = token_generator.gen_token_pair(user_id=dummy_user_id, username=dummy_username)

    # check token params
    decoded_access_token = jwt.decode(
        jwt=ret.access_token,
        key=setting.token.public_key,
        options={
            "verify_signature": True,
            "verify_aud": False,
            "verify_iss": False,
        },
        algorithms=["RS256"],
    )
    assert decoded_access_token["sub"] == dummy_user_id
    assert decoded_access_token["name"] == dummy_username
    iat = datetime.fromtimestamp(decoded_access_token["iat"], UTC)
    exp = datetime.fromtimestamp(decoded_access_token["exp"], UTC)
    nbf = datetime.fromtimestamp(decoded_access_token["nbf"], UTC)
    assert iat == NOW
    assert exp == NOW + timedelta(seconds=setting.token.access_duration)
    assert nbf == NOW - timedelta(seconds=1)

    # in range
    with time_machine.travel(
        NOW + timedelta(seconds=setting.token.access_duration - 1)
    ):
        jwt.decode(
            jwt=ret.access_token,
            key=setting.token.public_key,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
            },
            algorithms=["RS256"],
        )

    # expired
    with time_machine.travel(NOW + timedelta(seconds=setting.token.access_duration)):
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(
                jwt=ret.access_token,
                key=setting.token.public_key,
                options={
                    "verify_signature": True,
                    "verify_aud": False,
                    "verify_iss": False,
                },
                algorithms=["RS256"],
            )

    decoded_refresh_token = jwt.decode(
        jwt=ret.refresh_token,
        key=setting.token.public_key,
        options={
            "verify_signature": True,
            "verify_aud": False,
            "verify_iss": False,
        },
        algorithms=["RS256"],
    )
    assert decoded_refresh_token["sub"] == dummy_user_id
    assert decoded_refresh_token["name"] == dummy_username
    iat = datetime.fromtimestamp(decoded_refresh_token["iat"], UTC)
    exp = datetime.fromtimestamp(decoded_refresh_token["exp"], UTC)
    nbf = datetime.fromtimestamp(decoded_refresh_token["nbf"], UTC)
    assert iat == NOW
    assert exp == NOW + timedelta(seconds=setting.token.refresh_duration)
    assert nbf == NOW - timedelta(seconds=1)

    # in range
    with time_machine.travel(
        NOW + timedelta(seconds=setting.token.refresh_duration - 1)
    ):
        jwt.decode(
            jwt=ret.refresh_token,
            key=setting.token.public_key,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
            },
            algorithms=["RS256"],
        )

    # expired
    with time_machine.travel(NOW + timedelta(seconds=setting.token.refresh_duration)):
        with pytest.raises(ExpiredSignatureError):
            jwt.decode(
                jwt=ret.refresh_token,
                key=setting.token.public_key,
                options={
                    "verify_signature": True,
                    "verify_aud": False,
                    "verify_iss": False,
                },
                algorithms=["RS256"],
            )
