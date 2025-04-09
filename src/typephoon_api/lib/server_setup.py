from contextlib import asynccontextmanager
from logging import Filter, LogRecord, getLogger

from fastapi import APIRouter, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..api.auth import router as auth_router
from ..api.game import router as game_router
from ..api.healthcheck import router as healthcheck_router
from ..api.lobby import router as lobby_router
from ..api.profile import router as profile_router
from ..types.common import ErrorContext
from ..types.enums import ErrorCode
from ..types.responses.base import ErrorResponse
from ..types.setting import Setting
from .server import TypephoonServer

logger = getLogger(__name__)


class HealthCheckFilter(Filter):
    """disable access log for health check endpoints"""

    def filter(self, record: LogRecord):
        return record.getMessage().find("/healthcheck") == -1


@asynccontextmanager
async def lifespan(app: TypephoonServer):
    logger.info("lifespan startup")
    await app.prepare()
    getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    yield

    logger.info("lifespan shutdown")
    await app.cleanup()


async def validation_error_handler(_: Request, exc: Exception):
    logger.error("validation error: %s", exc)
    msg = jsonable_encoder(
        ErrorResponse(
            error=ErrorContext(code=ErrorCode.VALIDATION_ERROR, message=str(exc))
        )
    )
    return JSONResponse(status_code=422, content=msg)


def create_server(setting: Setting) -> TypephoonServer:
    app = TypephoonServer(setting=setting, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=setting.cors.allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(RequestValidationError, validation_error_handler)

    v1_router = APIRouter(
        prefix="/api/v1",
        responses={500: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
    )
    v1_router.include_router(auth_router)
    v1_router.include_router(lobby_router)
    v1_router.include_router(game_router)
    v1_router.include_router(profile_router)

    app.include_router(healthcheck_router)
    app.include_router(v1_router)

    return app
