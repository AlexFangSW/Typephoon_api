from fastapi import Request

from ..services.token import TokenService
from ..services.auth import AuthService
from .server import TypephoonServer
from ..services.health_check import HealthCheckService


async def get_health_check_service(request: Request) -> HealthCheckService:
    app: TypephoonServer = request.app
    service = HealthCheckService(app)
    return service


async def get_auth_service(request: Request) -> AuthService:
    app: TypephoonServer = request.app
    token_service = TokenService(app.setting)
    service = AuthService(setting=app.setting,
                          redis_conn=app.redis_conn,
                          sessionmaker=app.sessionmaker,
                          token_service=token_service)
    return service
