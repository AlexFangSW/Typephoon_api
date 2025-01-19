from logging import getLogger
from fastapi.datastructures import URL
from pydantic import BaseModel
from redis.asyncio import Redis

from .base import OAuthProviders, VerifyTokenRet

from ...lib.util import gen_user_id

from ...repositories.oauth_state import OAuthStateRepo

from ...types.setting import Setting
import jwt
from async_lru import alru_cache
from aiohttp import ClientSession

logger = getLogger(__name__)


@alru_cache(maxsize=1, ttl=60)
async def get_google_public_key() -> dict:
    async with ClientSession() as session:
        async with session.get("https://www.googleapis.com/oauth2/v3/certs") as resp:
            return await resp.json()


class GoogleTokenResponse(BaseModel):
    access_token: str
    expires_in: int
    scope: str
    id_token: str


class GoogleOAuthProvider:

    def __init__(
        self, setting: Setting, redis_conn: Redis, oauth_state_repo: OAuthStateRepo
    ) -> None:
        self._setting = setting
        self._redis_conn = redis_conn
        self._oauth_state_repo = oauth_state_repo

    async def get_authorization_url(self) -> URL:
        state = await self._oauth_state_repo.set_state()
        url = self._generate_url_for_login_redirect(state)
        return url

    async def handle_authorization_response(
        self, state: str, code: str
    ) -> VerifyTokenRet:
        if not await self._oauth_state_repo.state_exist(state):
            return VerifyTokenRet(ok=False)

        token = await self._exchange_code_for_token(code)
        verify_token_ret = await self._verify_token(token)
        return verify_token_ret

    def _generate_url_for_login_redirect(self, state: str) -> URL:
        params = {
            "response_type": "code",
            "client_id": self._setting.google.client_id,
            "scope": "openid email profile",
            "redirect_uri": self._setting.google.redirect_url,
            "state": state,
            "prompt": "select_account",
        }
        url = URL("https://accounts.google.com/o/oauth2/v2/auth")
        url = url.include_query_params(**params)
        return url

    async def _exchange_code_for_token(self, code: str) -> str:

        body = {
            "code": code,
            "client_id": self._setting.google.client_id,
            "client_secret": self._setting.google.client_secret,
            "redirect_uri": self._setting.google.redirect_url,
            "grant_type": "authorization_code",
        }

        async with ClientSession() as session:
            async with session.post(
                "https://oauth2.googleapis.com/token", json=body
            ) as resp:
                ret = await resp.json()
                data = GoogleTokenResponse.model_validate(ret)

        return data.id_token

    async def _verify_token(self, token: str) -> VerifyTokenRet:

        jwt_header_data = jwt.get_unverified_header(token)

        jwks_data = await get_google_public_key()

        public_key = None
        for key in jwks_data["keys"]:
            if key["kid"] == jwt_header_data["kid"]:  # type: ignore
                public_key = jwt.PyJWK.from_dict(key)
                break

        if not public_key:
            logger.warning("no matching public key found")
            return VerifyTokenRet(ok=False)

        decoded_jwt = jwt.decode(
            jwt=token,
            key=public_key,
            options={
                "verify_signature": True,
                "verify_aud": False,
                "verify_iss": False,
            },
        )

        user_id = gen_user_id(decoded_jwt["sub"], OAuthProviders.GOOGLE)
        username = decoded_jwt["name"]

        return VerifyTokenRet(ok=True, user_id=user_id, username=username)
