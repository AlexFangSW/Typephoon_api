from fastapi import Request

from .server import TypephoonServer
from ..services.health_check import HealthCheckService


async def create_health_check_service(request: Request) -> HealthCheckService:
    app: TypephoonServer = request.app
    service = HealthCheckService(app)
    return service
