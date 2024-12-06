from fastapi import APIRouter

router = APIRouter(tags=["Health Check"])


@router.post("/ready")
async def ready():
    ...


@router.post("/alive")
async def alive():
    ...
