from dataclasses import dataclass
from logging import getLogger
from typing import TypeVar
from fastapi.datastructures import URL
from aiohttp import ClientSession
import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from async_lru import alru_cache

from ..repositories.oauth_state import OAuthStateRepo

from .token import TokenService

from ..repositories.token import TokenRepo

from ..repositories.user import UserRepo

from ..types.setting import Setting

from .base import ServiceRet

from ..types.external.google import TokenResponse

logger = getLogger(__name__)


@dataclass(slots=True)
class LoginRedirectRet:
    url: str
    access_token: str
    refresh_token: str
    refresh_endpoint: str
    username: str


@dataclass(slots=True)
class VerifyGoogleTokenRet:
    ok: bool
    user_id: str | None = None
    username: str | None = None


T = TypeVar("T")


class AuthServiceRet(ServiceRet[T]):
    error_redirect_url: str | None = None


class AuthService:

    def __init__(
        self,
        setting: Setting,
        sessionmaker: async_sessionmaker[AsyncSession],
        token_service: TokenService,
        oauth_state_repo: OAuthStateRepo,
    ) -> None:
        self._setting = setting
        self._sessionmaker = sessionmaker
        self._token_service = token_service
        self._oauth_state_repo = oauth_state_repo

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

    async def login(self) -> AuthServiceRet[URL]:
        logger.debug("login")

        try:
            state = await self._oauth_state_repo.set_state()
            url = self._generate_url_for_login_redirect(state)
            return AuthServiceRet(ok=True, data=url)

        except:
            logger.exception("login redirect failed")
            return AuthServiceRet(
                ok=False, error_redirect_url=self._setting.error_redirect)

    async def _exchange_code_for_token(self, code: str) -> str:

        body = {
            "code": code,
            "client_id": self._setting.google.client_id,
            "client_secret": self._setting.google.client_secret,
            "redirect_uri": self._setting.google.redirect_url,
            "grant_type": "authorization_code"
        }

        async with ClientSession() as session:
            async with session.post("https://oauth2.googleapis.com/token",
                                    json=body) as resp:
                ret = await resp.json()
                data = TokenResponse.model_validate(ret)

        return data.id_token

    @alru_cache(maxsize=1, ttl=60)
    async def _get_google_public_key(self) -> dict:
        async with ClientSession() as session:
            async with session.get(
                    "https://www.googleapis.com/oauth2/v3/certs") as resp:
                return await resp.json()

    async def _verify_google_token(self, token: str) -> VerifyGoogleTokenRet:

        jwt_header_data = jwt.get_unverified_header(token)

        jwks_data = await self._get_google_public_key()

        public_key = None
        for key in jwks_data["keys"]:
            if key["kid"] == jwt_header_data["kid"]:  # type: ignore
                public_key = jwt.PyJWK.from_dict(key)
                break

        if not public_key:
            logger.warning("no matching public key found")
            return VerifyGoogleTokenRet(ok=False)

        decoded_jwt = jwt.decode(jwt=token,
                                 key=public_key,
                                 options={
                                     "verify_signature": True,
                                     "verify_aud": False,
                                     "verify_iss": False,
                                 })

        user_id = decoded_jwt['sub']
        username = decoded_jwt['name']

        return VerifyGoogleTokenRet(ok=True, user_id=user_id, username=username)

    async def login_redirect(self, state: str,
                             code: str) -> AuthServiceRet[LoginRedirectRet]:
        logger.debug("login_redirect")

        try:
            if not await self._oauth_state_repo.state_exist(state):
                return AuthServiceRet(
                    ok=False, error_redirect_url=self._setting.error_redirect)

            token = await self._exchange_code_for_token(code)
            verify_ret = await self._verify_google_token(token)
            if not verify_ret.ok:
                return AuthServiceRet(
                    ok=False, error_redirect_url=self._setting.error_redirect)

            assert verify_ret.user_id
            assert verify_ret.username

            async with self._sessionmaker() as session:
                user_repo = UserRepo(session)
                token_repo = TokenRepo(session)

                user = await user_repo.register_with_google(
                    id=verify_ret.user_id, name=verify_ret.username)

                gen_token_ret = self._token_service.gen_token_pair(
                    user_id=user.id, username=verify_ret.username)
                assert gen_token_ret.ok
                assert gen_token_ret.data

                await token_repo.set_refresh_token(
                    user_id=user.id,
                    refresh_token=gen_token_ret.data.refresh_token)

                await session.commit()

            data = LoginRedirectRet(
                url=self._setting.front_end_endpoint,
                access_token=gen_token_ret.data.access_token,
                refresh_token=gen_token_ret.data.refresh_token,
                username=verify_ret.username,
                refresh_endpoint=self._setting.token.refresh_endpoint,
            )
            return AuthServiceRet(ok=True, data=data)

        except:
            logger.exception("login redirect failed")
            return AuthServiceRet(
                ok=False, error_redirect_url=self._setting.error_redirect)

    async def logout(self) -> AuthServiceRet:
        """
        Removes refresh token from db
        """
        logger.debug("logout")

        try:
            async with self._sessionmaker() as session:
                ...
                await session.commit()

            return AuthServiceRet(ok=True)
        except:
            logger.exception("logout failed")
            return AuthServiceRet(
                ok=False, error_redirect_url=self._setting.error_redirect)

    async def token_refresh(self) -> AuthServiceRet:
        """
        - 
        - Generate new access token
        """
        logger.debug("token_refresh")

        try:
            # get refresh token
            async with self._sessionmaker() as session:
                ...
            # is the refresh token valid

            # check if refresh token is the same in DB

            # generate access token
        except:
            ...
        ...
