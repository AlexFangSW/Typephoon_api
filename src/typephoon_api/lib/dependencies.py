from fastapi import Request

from ..services.auth import AuthService

from .server import TypephoonServer
from ..services.health_check import HealthCheckService


async def get_health_check_service(request: Request) -> HealthCheckService:
    app: TypephoonServer = request.app
    service = HealthCheckService(app)
    return service


async def get_auth_service(request: Request) -> AuthService:
    app: TypephoonServer = request.app
    service = AuthService(app)
    return service
