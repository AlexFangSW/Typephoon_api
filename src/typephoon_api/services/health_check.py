from ..lib.server import TypephoonServer
from .base import ServiceRet


class HealthCheckService:
    def __init__(self, app: TypephoonServer) -> None:
        self._app = app

    async def alive(self) -> ServiceRet:
        return ServiceRet(ok=True)

    async def ready(self) -> ServiceRet:
        result = await self._app.ready()
        return ServiceRet(ok=result)
