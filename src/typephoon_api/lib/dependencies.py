from dataclasses import dataclass
from logging import getLogger
from fastapi import Cookie, Request
from fastapi.security.api_key import Annotated
from jwt.exceptions import PyJWTError

from ..types.errors import InvalidCookieToken

from ..types.common import ErrorContext

from ..types.jwt import JWTPayload

from ..types.enums import CookieNames, ErrorCode

from ..services.lobby import LobbyService

from ..repositories.game_cache import GameCacheRepo

from ..repositories.guest_token import GuestTokenRepo

from ..services.queue_in import QueueInService

from .oauth_providers.base import OAuthProviders

from ..types.setting import Setting

from .token_validator import TokenValidator

from ..lib.oauth_providers.google import GoogleOAuthProvider
from ..repositories.oauth_state import OAuthStateRepo

from .token_generator import TokenGenerator

from ..services.auth import AuthService
from .server import TypephoonServer
from ..services.health_check import HealthCheckService
from . import token_validator

logger = getLogger(__name__)


async def get_health_check_service(request: Request) -> HealthCheckService:
    app: TypephoonServer = request.app
    service = HealthCheckService(app)
    return service


async def get_auth_service_with_provider(
        request: Request, provider: OAuthProviders) -> AuthService:
    app: TypephoonServer = request.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)
    oauth_state_repo = OAuthStateRepo(setting=app.setting,
                                      redis_conn=app.redis_conn)

    if provider == OAuthProviders.GOOGLE:
        oauth_provider = GoogleOAuthProvider(setting=app.setting,
                                             redis_conn=app.redis_conn,
                                             oauth_state_repo=oauth_state_repo)

    service = AuthService(setting=app.setting,
                          sessionmaker=app.sessionmaker,
                          oauth_provider=oauth_provider,
                          token_validator=token_validator,
                          token_generator=token_generator)
    return service


async def get_auth_service(request: Request) -> AuthService:
    app: TypephoonServer = request.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)

    service = AuthService(setting=app.setting,
                          sessionmaker=app.sessionmaker,
                          token_validator=token_validator,
                          token_generator=token_generator)
    return service


async def get_lobby_service(request: Request) -> LobbyService:
    app: TypephoonServer = request.app
    game_cache_repo = GameCacheRepo(redis_conn=app.redis_conn,
                                    setting=app.setting)
    service = LobbyService(setting=app.setting,
                           game_cache_repo=game_cache_repo,
                           sessionmaker=app.sessionmaker)
    return service


async def get_queue_in_service(request: Request) -> QueueInService:
    app: TypephoonServer = request.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)
    guest_token_repo = GuestTokenRepo(redis_conn=app.redis_conn,
                                      setting=app.setting)
    game_cache_repo = GameCacheRepo(redis_conn=app.redis_conn,
                                    setting=app.setting)

    service = QueueInService(setting=app.setting,
                             token_validator=token_validator,
                             token_generator=token_generator,
                             background_bucket=app.lobby_background_bucket,
                             guest_token_repo=guest_token_repo,
                             sessionmaker=app.sessionmaker,
                             amqp_notify_exchange=app.amqp_notify_exchange,
                             amqp_default_exchange=app.amqp_default_exchange,
                             game_cache_repo=game_cache_repo)
    return service


def get_setting(request: Request) -> Setting:
    app: TypephoonServer = request.app
    return app.setting


def get_access_token_info(
    request: Request,
    access_token: Annotated[str, Cookie(alias=CookieNames.ACCESS_TOKEN)]
) -> JWTPayload:
    """
    validate 'access' token and return payload
    """
    app: TypephoonServer = request.app
    try:
        token_validator = TokenValidator(app.setting)
        return token_validator.validate(access_token)
    except PyJWTError as ex:
        raise InvalidCookieToken(str(ex))
