from fastapi import APIRouter

router = APIRouter(tags=["Health Check"])


@router.get("/ready")
async def ready():
    ...


@router.get("/alive")
async def alive():
    ...
