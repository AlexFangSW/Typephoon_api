from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..lib.server import TypephoonServer

router = APIRouter(tags=["Health Check"])


@router.get("/ready")
async def ready(request: Request):
    app: TypephoonServer = request.app
    await app.ready()
    return JSONResponse({"ready": True})


@router.get("/alive")
async def alive():
    return JSONResponse({"alive": True})
