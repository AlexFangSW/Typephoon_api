from datetime import timedelta
from jwt.exceptions import ExpiredSignatureError
import pytest
import time_machine

from ...lib.oauth_providers.base import OAuthProviders

from ...lib.token_validator import TokenValidator

from ...lib.util import gen_user_id

from ...lib.token_generator import TokenGenerator
from ..helper import *


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
async def test_token_validator(setting: Setting):
    token_generator = TokenGenerator(setting=setting)
    token_validator = TokenValidator(setting=setting)

    dummy_google_user_id = "user_id"
    dummy_user_id = gen_user_id(dummy_google_user_id, OAuthProviders.GOOGLE)
    dummy_username = "username"

    token = token_generator.gen_access_token(user_id=dummy_user_id,
                                             username=dummy_username)

    info = token_validator.validate(token)
    assert info.sub == dummy_user_id
    assert info.name == dummy_username
    iat = datetime.fromtimestamp(info.iat, UTC)
    exp = datetime.fromtimestamp(info.exp, UTC)
    nbf = datetime.fromtimestamp(info.nbf, UTC)
    assert iat == NOW
    assert exp == NOW + timedelta(seconds=setting.token.access_duration)
    assert nbf == NOW - timedelta(seconds=1)

    # expired
    with time_machine.travel(NOW +
                             timedelta(seconds=setting.token.access_duration)):
        with pytest.raises(ExpiredSignatureError):
            token_validator.validate(token)
