from contextlib import asynccontextmanager
from logging import getLogger
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ..api.health_check import router as health_check_router
from ..api.auth import router as auth_router

from ..types.setting import Setting
from ..api import auth

logger = getLogger(__name__)


class TypephoonServer(FastAPI):

    def __init__(self, setting: Setting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setting = setting

    async def prepare(self):
        # TODO: postgresql
        # TODO: redis
        ...

    async def cleanup(self):
        ...


@asynccontextmanager
async def lifespan(app: TypephoonServer):
    logger.info("lifespan startup")
    await app.prepare()

    yield

    logger.info("lifespan shutdown")
    await app.cleanup()


def create_server(setting: Setting) -> TypephoonServer:
    app = TypephoonServer(setting=setting, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=setting.cors.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1_router = APIRouter(prefix="/api/v1")
    v1_router.include_router(auth_router)

    app.include_router(health_check_router)
    app.include_router(v1_router)

    return app
