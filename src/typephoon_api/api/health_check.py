from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..lib.server import TypephoonServer

router = APIRouter(tags=["Health Check"], prefix="/healthcheck")


@router.get("/ready")
async def ready(request: Request):
    app: TypephoonServer = request.app
    ready = await app.ready()
    if ready:
        return JSONResponse({"ready": True})
    return JSONResponse({"ready": False}, status_code=500)


@router.get("/alive")
async def alive():
    return JSONResponse({"alive": True})
