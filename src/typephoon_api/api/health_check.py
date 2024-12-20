from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..lib.util import catch_error_async

from ..lib.dependencies import get_health_check_service

from ..services.health_check import HealthCheckService

from ..schemas.responses.base import ErrorResponse, SuccessResponse

router = APIRouter(tags=["Health Check"], prefix="/healthcheck")


@router.get("/ready",
            responses={
                200: {
                    "model": SuccessResponse
                },
                500: {
                    "model": ErrorResponse
                }
            })
@catch_error_async
async def ready(health_check_service: HealthCheckService = Depends(
    get_health_check_service)):

    ready = await health_check_service.ready()

    if ready:
        msg = SuccessResponse().model_dump()
        return JSONResponse(msg, status_code=200)

    msg = ErrorResponse().model_dump()
    return JSONResponse(msg, status_code=500)


@router.get("/alive", responses={200: {"model": SuccessResponse}})
@catch_error_async
async def alive(health_check_service: HealthCheckService = Depends(
    get_health_check_service)):

    if await health_check_service.alive():
        msg = SuccessResponse().model_dump()
        return JSONResponse(msg, status_code=200)
