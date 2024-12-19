from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..lib.dependencies import create_health_check_service

from ..services.health_check import HealthCheckService

from ..schemas.responses.base import ErrorResponse, SuccessResponse

router = APIRouter(tags=["Health Check"], prefix="/healthcheck")


@router.get("/ready",
            responses={
                status.HTTP_200_OK: {
                    "model": SuccessResponse
                },
                status.HTTP_500_INTERNAL_SERVER_ERROR: {
                    "model": ErrorResponse
                }
            })
async def ready(health_check_service: HealthCheckService = Depends(
    create_health_check_service)):
    ready = await health_check_service.ready()
    if ready:
        return JSONResponse(
            SuccessResponse().model_dump(),
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        ErrorResponse().model_dump(),
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@router.get("/alive",
            responses={status.HTTP_200_OK: {
                "model": SuccessResponse
            }})
async def alive(health_check_service: HealthCheckService = Depends(
    create_health_check_service)):
    if await health_check_service.alive():
        return JSONResponse(
            SuccessResponse().model_dump(),
            status_code=status.HTTP_200_OK,
        )
