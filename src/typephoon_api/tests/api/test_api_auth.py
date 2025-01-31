from ...lib.token_validator import TokenValidator
from ...repositories.guest_token import GuestTokenRepo
from ...lib.token_generator import TokenGenerator
from ...types.enums import CookieNames, UserType
from ..helper import *


@pytest.mark.asyncio
async def test_api_auth_guest_token(
    client: AsyncClient, redis_conn: Redis, setting: Setting
):
    token_generator = TokenGenerator(setting)
    user_id = "user_id"
    username = "username"
    guest_token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.GUEST
    )
    repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    key = await repo.store(guest_token)

    ret = await client.get(f"{API_PREFIX}/auth/guest-token", params={"key": key})
    assert ret.status_code == 200
    token_validator = TokenValidator(setting)
    data = token_validator.validate(ret.cookies[CookieNames.ACCESS_TOKEN])
    assert data.name == username
    assert data.user_type == UserType.GUEST
    assert data.sub == user_id
