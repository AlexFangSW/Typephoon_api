from dataclasses import dataclass
from logging import getLogger
from typing import Annotated

from fastapi import Cookie, Request, WebSocket
from jwt.exceptions import PyJWTError

from ..lib.oauth_providers.google import GoogleOAuthProvider
from ..repositories.game_cache import GameCacheRepo
from ..repositories.guest_token import GuestTokenRepo
from ..repositories.lobby_cache import LobbyCacheRepo
from ..repositories.oauth_state import OAuthStateRepo
from ..services.auth import AuthService
from ..services.game import GameService
from ..services.game_event import GameEventService
from ..services.health_check import HealthCheckService
from ..services.lobby import LobbyService
from ..services.profile import ProfileService
from ..services.queue_in import QueueInService
from ..types.enums import CookieNames
from ..types.jwt import JWTPayload
from ..types.setting import Setting
from .oauth_providers.base import OAuthProviders
from .server import TypephoonServer
from .token_generator import TokenGenerator
from .token_validator import TokenValidator

logger = getLogger(__name__)


async def get_health_check_service(request: Request) -> HealthCheckService:
    app: TypephoonServer = request.app
    service = HealthCheckService(app)
    return service


async def get_auth_service_with_provider(
    request: Request, provider: OAuthProviders
) -> AuthService:
    app: TypephoonServer = request.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)
    oauth_state_repo = OAuthStateRepo(setting=app.setting, redis_conn=app.redis_conn)
    guest_token_repo = GuestTokenRepo(redis_conn=app.redis_conn, setting=app.setting)

    if provider == OAuthProviders.GOOGLE:
        oauth_provider = GoogleOAuthProvider(
            setting=app.setting,
            redis_conn=app.redis_conn,
            oauth_state_repo=oauth_state_repo,
        )

    service = AuthService(
        setting=app.setting,
        sessionmaker=app.sessionmaker,
        oauth_provider=oauth_provider,
        token_validator=token_validator,
        token_generator=token_generator,
        guest_token_repo=guest_token_repo,
    )
    return service


async def get_auth_service(request: Request) -> AuthService:
    app: TypephoonServer = request.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)
    guest_token_repo = GuestTokenRepo(redis_conn=app.redis_conn, setting=app.setting)

    service = AuthService(
        setting=app.setting,
        sessionmaker=app.sessionmaker,
        token_validator=token_validator,
        token_generator=token_generator,
        guest_token_repo=guest_token_repo,
    )
    return service


async def get_lobby_service(request: Request) -> LobbyService:
    app: TypephoonServer = request.app
    lobby_cache_repo = LobbyCacheRepo(redis_conn=app.redis_conn, setting=app.setting)
    service = LobbyService(
        setting=app.setting,
        lobby_cache_repo=lobby_cache_repo,
        amqp_notify_exchange=app.amqp_notify_exchange,
        sessionmaker=app.sessionmaker,
    )
    return service


async def get_queue_in_service(ws: WebSocket) -> QueueInService:
    app: TypephoonServer = ws.app

    token_generator = TokenGenerator(app.setting)
    token_validator = TokenValidator(app.setting)
    guest_token_repo = GuestTokenRepo(redis_conn=app.redis_conn, setting=app.setting)
    lobby_cache_repo = LobbyCacheRepo(redis_conn=app.redis_conn, setting=app.setting)
    game_cache_repo = GameCacheRepo(redis_conn=app.redis_conn, setting=app.setting)

    service = QueueInService(
        setting=app.setting,
        token_validator=token_validator,
        token_generator=token_generator,
        bg_manager=app.lobby_bg_manager,
        guest_token_repo=guest_token_repo,
        sessionmaker=app.sessionmaker,
        amqp_notify_exchange=app.amqp_notify_exchange,
        amqp_default_exchange=app.amqp_default_exchange,
        game_cache_repo=game_cache_repo,
        lobby_cache_repo=lobby_cache_repo,
    )
    return service


async def get_game_event_service(ws: WebSocket) -> GameEventService:
    app: TypephoonServer = ws.app

    token_validator = TokenValidator(app.setting)
    game_cache_repo = GameCacheRepo(redis_conn=app.redis_conn, setting=app.setting)

    service = GameEventService(
        token_validator=token_validator,
        game_cache_repo=game_cache_repo,
        bg_manager=app.game_bg_manager,
        keystroke_exchange=app.amqp_keystroke_exchange,
        setting=app.setting,
    )
    return service


async def get_game_service(request: Request) -> GameService:
    app: TypephoonServer = request.app

    game_cache_repo = GameCacheRepo(redis_conn=app.redis_conn, setting=app.setting)

    service = GameService(
        sessionmaker=app.sessionmaker, game_cache_repo=game_cache_repo
    )
    return service


async def get_profile_service(request: Request) -> ProfileService:
    app: TypephoonServer = request.app
    service = ProfileService(sessionmaker=app.sessionmaker)
    return service


def get_setting(request: Request) -> Setting:
    app: TypephoonServer = request.app
    return app.setting


@dataclass(slots=True)
class GetAccessTokenInfoRet:
    payload: JWTPayload | None = None
    error: Exception | None = None


def get_access_token_info(
    request: Request,
    access_token: Annotated[
        str, Cookie(alias=CookieNames.ACCESS_TOKEN, description="access token")
    ],
) -> GetAccessTokenInfoRet:
    """
    validate 'access' token and return payload
    """
    app: TypephoonServer = request.app
    try:
        token_validator = TokenValidator(app.setting)
        return GetAccessTokenInfoRet(payload=token_validator.validate(access_token))
    except PyJWTError as ex:
        return GetAccessTokenInfoRet(error=ex)
