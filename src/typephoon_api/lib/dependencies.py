from logging import getLogger
from fastapi import Request

from .oauth_providers.base import OAuthProviders

from ..types.setting import Setting

from .token_validator import TokenValidator

from ..lib.oauth_providers.google import GoogleOAuthProvider
from ..repositories.oauth_state import OAuthStateRepo

from .token_generator import TokenGenerator

from ..services.auth import AuthService
from .server import TypephoonServer
from ..services.health_check import HealthCheckService

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


def get_setting(request: Request) -> Setting:
    app: TypephoonServer = request.app
    return app.setting
