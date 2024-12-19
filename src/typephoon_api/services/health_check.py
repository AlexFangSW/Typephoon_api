from ..lib.server import TypephoonServer


class HealthCheckService:

    def __init__(self, app: TypephoonServer) -> None:
        self._app = app

    async def alive(self) -> bool:
        return True

    async def ready(self) -> bool:
        return await self._app.ready()
