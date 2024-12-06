from fastapi import APIRouter

router = APIRouter(tags=["Auth"])


@router.post("/login")
async def login():
    ...


@router.post("/logout")
async def logout():
    ...


@router.post("/token/refresh")
async def token_refresh():
    ...


@router.post("/register")
async def register():
    ...


@router.websocket("/ws/token")
async def ws_token(websocket: WebSocket):
    ...
