from dataclasses import dataclass
from logging import getLogger
from typing import TypeVar
from fastapi.datastructures import URL
from jwt.exceptions import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..lib.oauth_providers.base import OAuthProvider

from ..types.common import ErrorContext
from ..types.enums import ErrorCode

from ..lib.token_validator import TokenValidator

from ..lib.token_generator import TokenGenerator

from ..repositories.token import TokenRepo

from ..repositories.user import UserRepo

from ..types.setting import Setting

from .base import ServiceRet
from pydantic import BaseModel, ConfigDict

logger = getLogger(__name__)


class UserNameAndID(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str


@dataclass(slots=True)
class LoginRedirectRet:
    url: str
    access_token: str
    refresh_token: str
    refresh_endpoint: str
    username: str
    id: str


T = TypeVar("T")


class AuthService:

    def __init__(self,
                 setting: Setting,
                 sessionmaker: async_sessionmaker[AsyncSession],
                 token_generator: TokenGenerator,
                 token_validator: TokenValidator,
                 oauth_provider: OAuthProvider | None = None) -> None:
        self._setting = setting
        self._sessionmaker = sessionmaker
        self._token_generator = token_generator
        self._token_validator = token_validator
        self._oauth_provider = oauth_provider

    async def login(self) -> ServiceRet[URL]:
        logger.debug("login")

        try:
            assert self._oauth_provider
            url = await self._oauth_provider.get_authorization_url()
            return ServiceRet(ok=True, data=url)

        except:
            logger.exception("login redirect failed")
            return ServiceRet(ok=False)

    async def login_redirect(self, state: str,
                             code: str) -> ServiceRet[LoginRedirectRet]:
        logger.debug("login_redirect")

        try:
            assert self._oauth_provider
            handle_auth_ret = await self._oauth_provider.handle_authorization_response(
                state=state, code=code)

            if not handle_auth_ret.ok:
                return ServiceRet(ok=False)

            assert handle_auth_ret.user_id
            assert handle_auth_ret.username

            async with self._sessionmaker() as session:
                user_repo = UserRepo(session)
                token_repo = TokenRepo(session)

                ret = await user_repo.register(id=handle_auth_ret.user_id,
                                               name=handle_auth_ret.username)
                user = UserNameAndID.model_validate(ret)

                gen_token_ret = self._token_generator.gen_token_pair(
                    user_id=user.id, username=user.name)

                await token_repo.set_refresh_token(
                    user_id=user.id, refresh_token=gen_token_ret.refresh_token)

                await session.commit()

            data = LoginRedirectRet(
                url=self._setting.front_end_endpoint,
                access_token=gen_token_ret.access_token,
                refresh_token=gen_token_ret.refresh_token,
                username=user.name,
                refresh_endpoint=self._setting.token.refresh_endpoint,
                id=user.id,
            )
            return ServiceRet(ok=True, data=data)

        except:
            logger.exception("login redirect failed")
            return ServiceRet(ok=False)

    async def logout(self, access_token: str) -> ServiceRet:
        """
        Removes refresh token from db
        """
        logger.debug("logout")

        try:
            info = self._token_validator.validate(access_token)
        except PyJWTError:
            # The client can't do anything with a invalied token,
            # they are basically logged out.
            return ServiceRet(ok=True)

        async with self._sessionmaker() as session:
            token_repo = TokenRepo(session)
            await token_repo.remove_refresh_token(info.sub)
            await session.commit()

        return ServiceRet(ok=True)

    async def token_refresh(self, refresh_token: str) -> ServiceRet[str]:
        """
        Generate new access token
        """
        logger.debug("token_refresh")

        # is the refresh token valid
        try:
            info = self._token_validator.validate(refresh_token)
        except PyJWTError as ex:
            logger.warning("invalid token, token: %s, error: %s", refresh_token,
                           str(ex))
            error = ErrorContext(code=ErrorCode.INVALID_TOKEN, message=str(ex))
            return ServiceRet(ok=False, error=error)

        # check if refresh token is the same in DB
        async with self._sessionmaker() as session:
            repo = TokenRepo(session)
            token_in_db = await repo.get_refresh_token(info.sub)

        if token_in_db != refresh_token:
            logger.warning(
                "refresh token missmatch, got token: %s, db token: %s",
                refresh_token, token_in_db)
            error = ErrorContext(code=ErrorCode.REFRESH_TOKEN_MISSMATCH)
            return ServiceRet(ok=False, error=error)

        # generate access token
        new_access_token = self._token_generator.gen_access_token(
            info.sub, info.name)

        return ServiceRet(ok=True, data=new_access_token)
