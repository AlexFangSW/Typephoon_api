from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..lib.util import catch_error_async

from ..lib.dependencies import get_health_check_service

from ..services.health_check import HealthCheckService

from ..types.responses.base import ErrorResponse, SuccessResponse

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
async def ready(
        service: HealthCheckService = Depends(get_health_check_service)):

    result = await service.ready()

    if result.ok:
        msg = jsonable_encoder(SuccessResponse())
        return JSONResponse(msg, status_code=200)

    msg = jsonable_encoder(ErrorResponse())
    return JSONResponse(msg, status_code=500)


@router.get("/alive", responses={200: {"model": SuccessResponse}})
@catch_error_async
async def alive(
        service: HealthCheckService = Depends(get_health_check_service)):

    result = await service.alive()

    if result.ok:
        msg = jsonable_encoder(SuccessResponse())
        return JSONResponse(msg, status_code=200)

    raise ValueError("this should never happen !!")
