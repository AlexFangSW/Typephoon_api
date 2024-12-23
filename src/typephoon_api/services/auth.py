from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from logging import getLogger
from os import urandom
from typing import TypeVar
from fastapi.datastructures import URL
from aiohttp import ClientSession
import jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from async_lru import alru_cache

from ..repositories.token import TokenRepo

from ..repositories.user import UserRepo
from ..types.enums import UserType

from ..types.jwt import JWTPayload

from ..types.setting import Setting

from .base import ServiceRet

from ..types.external.google import TokenResponse

from ..lib.util import gen_user_id, get_state_key
from hashlib import sha256

logger = getLogger(__name__)


@dataclass(slots=True)
class LoginRet:
    url: URL


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


@dataclass(slots=True)
class GenerateTokensRet:
    access_token: str
    refresh_token: str


T = TypeVar("T")


class AuthServiceRet(ServiceRet[T]):
    error_redirect_url: str | None = None


class AuthService:

    def __init__(
        self,
        setting: Setting,
        redis_conn: Redis,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> None:
        self._setting = setting
        self._redis_conn = redis_conn
        self._sessionmaker = sessionmaker

    async def _set_state_in_redis(self) -> str:
        state = sha256(urandom(1024)).hexdigest()
        key = get_state_key(state)
        await self._redis_conn.set(
            key,
            1,
            ex=self._setting.redis.expire_time,
            nx=True,
        )
        return state

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

    async def login(self) -> AuthServiceRet[LoginRet]:
        logger.debug("login")

        try:
            state = await self._set_state_in_redis()
            url = self._generate_url_for_login_redirect(state)
            return AuthServiceRet(ok=True, data=LoginRet(url=url))

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

    async def _check_state(self, state: str) -> bool:
        key = get_state_key(state)
        exist = await self._redis_conn.getdel(key)

        if not exist:
            logger.warning("key not found, key: %s", key)
            return False

        return True

    def _generate_tokens(self, user_id: str,
                         username: str) -> GenerateTokensRet:
        iat = datetime.now(UTC)
        nbf = (iat - timedelta(seconds=1))

        access_exp = iat + timedelta(
            seconds=self._setting.token.access_duration)
        access_payload = JWTPayload(sub=user_id,
                                    name=username,
                                    exp=int(access_exp.timestamp()),
                                    nbf=int(nbf.timestamp()),
                                    iat=int(iat.timestamp()))

        access_token = jwt.encode(asdict(access_payload),
                                  self._setting.token.private_key,
                                  algorithm="RS256")

        refresh_exp = iat + timedelta(
            seconds=self._setting.token.refresh_duration)
        refresh_payload = JWTPayload(sub=user_id,
                                     name=username,
                                     exp=int(refresh_exp.timestamp()),
                                     nbf=int(nbf.timestamp()),
                                     iat=int(iat.timestamp()))
        refresh_token = jwt.encode(asdict(refresh_payload),
                                   self._setting.token.private_key,
                                   algorithm="RS256")

        return GenerateTokensRet(access_token=access_token,
                                 refresh_token=refresh_token)

    async def _update_user_refresh_token(self, user_id: str,
                                         refresh_token: str):
        async with self._sessionmaker() as session:
            repo = TokenRepo(session)
            await repo.set_refresh_token(user_id=user_id,
                                         refresh_token=refresh_token)
            await session.commit()

    async def _register_user(self, user_id: str, name: str):
        async with self._sessionmaker() as session:
            repo = UserRepo(session)
            await repo.create(id=user_id,
                              name=name,
                              user_type=UserType.REGISTERED)
            await session.commit()

    async def login_redirect(self, state: str,
                             code: str) -> AuthServiceRet[LoginRedirectRet]:
        logger.debug("login_redirect")

        try:
            exist = await self._check_state(state)
            if not exist:
                return AuthServiceRet(
                    ok=False, error_redirect_url=self._setting.error_redirect)

            token = await self._exchange_code_for_token(code)
            verify_ret = await self._verify_google_token(token)
            if not verify_ret.ok:
                return AuthServiceRet(
                    ok=False, error_redirect_url=self._setting.error_redirect)

            assert verify_ret.user_id
            assert verify_ret.username
            user_id = gen_user_id(verify_ret.user_id)

            new_tokens = self._generate_tokens(user_id=user_id,
                                               username=verify_ret.username)
            await self._register_user(user_id=user_id, name=verify_ret.username)
            await self._update_user_refresh_token(
                user_id=user_id, refresh_token=new_tokens.refresh_token)

            data = LoginRedirectRet(
                url=self._setting.front_end_endpoint,
                access_token=new_tokens.access_token,
                refresh_token=new_tokens.refresh_token,
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
