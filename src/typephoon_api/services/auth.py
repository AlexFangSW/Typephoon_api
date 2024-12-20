from os import urandom
from fastapi.datastructures import URL

from ..lib.util import get_state_key
from ..lib.server import TypephoonServer
from hashlib import sha256


class AuthService:

    def __init__(self, app: TypephoonServer) -> None:
        self._app = app

    async def login(self) -> URL:
        # Set state in redis
        state = sha256(urandom(1024)).hexdigest()
        key = get_state_key(state)
        await self._app.redis_conn.set(
            key,
            1,
            ex=self._app.setting.redis.expire_time,
            nx=True,
        )

        # generate url for redirect
        params = {
            "response_type": "code",
            "client_id": self._app.setting.google.client_id,
            "scope": "openid email profile",
            "redirect_uri": self._app.setting.google.redirect_url,
            "state": state,
            "prompt": "select_account",
        }
        url = URL("https://accounts.google.com/o/oauth2/v2/auth")
        url = url.include_query_params(**params)

        return url

    async def logout(self):
        ...

    async def token_refresh(self):
        ...
