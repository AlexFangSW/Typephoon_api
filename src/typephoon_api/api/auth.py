from fastapi import APIRouter, WebSocket

router = APIRouter(tags=["Auth"], prefix="/auth")


@router.post("/login")
async def login():
    ...


@router.post("/logout")
async def logout():
    ...


@router.post("/token/refresh")
async def token_refresh():
    ...


@router.websocket("/ws/token")
async def ws_token(websocket: WebSocket):
    ...
