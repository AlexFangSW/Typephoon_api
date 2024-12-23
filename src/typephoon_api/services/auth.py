from dataclasses import dataclass
from logging import getLogger
from typing import TypeVar
from fastapi.datastructures import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..oauth_providers.base import OAuthProvider

from ..lib.token_generator import TokenGenerator

from ..repositories.token import TokenRepo

from ..repositories.user import UserRepo

from ..types.setting import Setting

from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class LoginRedirectRet:
    url: str
    access_token: str
    refresh_token: str
    refresh_endpoint: str
    username: str


T = TypeVar("T")


class AuthServiceRet(ServiceRet[T]):
    error_redirect_url: str | None = None


class AuthService:

    def __init__(self, setting: Setting,
                 sessionmaker: async_sessionmaker[AsyncSession],
                 token_generator: TokenGenerator,
                 oauth_provider: OAuthProvider) -> None:
        self._setting = setting
        self._sessionmaker = sessionmaker
        self._token_generator = token_generator
        self._oauth_provider = oauth_provider

    async def login(self) -> AuthServiceRet[URL]:
        logger.debug("login")

        try:
            url = await self._oauth_provider.get_authorization_url()
            return AuthServiceRet(ok=True, data=url)

        except:
            logger.exception("login redirect failed")
            return AuthServiceRet(
                ok=False, error_redirect_url=self._setting.error_redirect)

    async def login_redirect(self, state: str,
                             code: str) -> AuthServiceRet[LoginRedirectRet]:
        logger.debug("login_redirect")

        try:
            verify_ret = await self._oauth_provider.handle_authorization_response(
                state=state, code=code)

            if not verify_ret.ok:
                return AuthServiceRet(
                    ok=False, error_redirect_url=self._setting.error_redirect)

            assert verify_ret.user_id
            assert verify_ret.username

            async with self._sessionmaker() as session:
                user_repo = UserRepo(session)
                token_repo = TokenRepo(session)

                user = await user_repo.register(id=verify_ret.user_id,
                                                name=verify_ret.username)

                gen_token_ret = self._token_generator.gen_token_pair(
                    user_id=user.id, username=user.name)

                await token_repo.set_refresh_token(
                    user_id=user.id, refresh_token=gen_token_ret.refresh_token)

                await session.commit()

            data = LoginRedirectRet(
                url=self._setting.front_end_endpoint,
                access_token=gen_token_ret.access_token,
                refresh_token=gen_token_ret.refresh_token,
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

    async def token_refresh(self):
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
