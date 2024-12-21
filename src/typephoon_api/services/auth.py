from logging import getLogger
from os import urandom
from fastapi.datastructures import URL
from aiohttp import ClientSession
import jwt

from ..repositories.user import UserRepo

from ..types.services.auth import LoginRedirectData

from ..types.external.google import TokenResponse

from ..types.services.base import ServiceRet

from ..lib.util import get_state_key
from ..lib.server import TypephoonServer
from hashlib import sha256

logger = getLogger(__name__)


class AuthService:

    def __init__(self, app: TypephoonServer) -> None:
        self._app = app

    async def login(self) -> ServiceRet[URL]:
        logger.debug("login")

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

        return ServiceRet(data=url)

    async def login_redirect(self, state: str,
                             code: str) -> ServiceRet[LoginRedirectData]:
        logger.debug("login_redirect")

        # check if state exist
        key = get_state_key(state)
        exist = await self._app.redis_conn.getdel(key)
        if not exist:
            logger.warning("key not found, key: %s", key)
            redirect_url = URL(self._app.setting.server.error_redirect)
            return ServiceRet(success=False, error_redirect=redirect_url)

        # use code to get the token
        body = {
            "code": code,
            "client_id": self._app.setting.google.client_id,
            "client_secret": self._app.setting.google.client_secret,
            "redirect_uri": self._app.setting.google.redirect_url,
            "grant_type": "authorization_code"
        }

        async with ClientSession() as session:
            async with session.post("https://oauth2.googleapis.com/token",
                                    json=body) as resp:
                ret = await resp.json()
                data = TokenResponse.model_validate(ret)

        # verify token
        jwt_header_data = jwt.get_unverified_header(data.id_token)

        async with ClientSession() as session:
            async with session.get(
                    "https://www.googleapis.com/oauth2/v3/certs") as resp:
                jwks_data = await resp.json()

        public_key = None
        for key in jwks_data["keys"]:
            if key["kid"] == jwt_header_data["kid"]:
                public_key = jwt.PyJWK.from_dict(key)
                break

        if not public_key:
            logger.warning("no matching public key found")
            redirect_url = URL(self._app.setting.server.error_redirect)
            return ServiceRet(success=False, error_redirect=redirect_url)

        decoed_jwt = jwt.decode(jwt=data.id_token,
                                key=public_key,
                                options={
                                    "verify_signature": True,
                                    "verify_aud": False,
                                    "verify_iss": False,
                                })

        # extract needed info
        google_user_id = decoed_jwt['sub']
        google_username = decoed_jwt['name']

        # TODO: register user if needed
        async with self._app.sessionmaker() as session:
            repo = UserRepo(session)
            user_info = await repo.insert(id=google_user_id,
                                          name=google_username)
            await session.commit()

        # TODO: generate access and refresh token
        access_token = jwt.encode({"some": "payload"},
                                  "secret",
                                  algorithm="RS256")
        refresh_token = jwt.encode({"some": "payload"},
                                   "secret",
                                   algorithm="RS256")

        # TODO: save refresh token

        data = LoginRedirectData(
            url=self._app.setting.server.front_end_endpoint,
            access_token=access_token,
            refresh_token=refresh_token,
            username=user_info.name,
            refresh_endpoint=self._app.setting.token.refresh_endpoint,
        )
        return ServiceRet(success=True, data=data)

    async def logout(self):
        logger.debug("logout")
        ...

    async def token_refresh(self):
        logger.debug("token_refresh")
        ...
