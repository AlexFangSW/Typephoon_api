from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, Query, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.util import await_only

from ..services.queue_in import QueueInService

from ..types.setting import Setting

from ..types.responses.base import ErrorResponse, SuccessResponse

from ..types.enums import CookieNames, ErrorCode, QueueInType

from ..lib.dependencies import get_auth_service, get_auth_service_with_provider, get_setting
from ..services.auth import AuthService

from ..lib.util import catch_error_async

router = APIRouter(tags=["Lobby"],
                   prefix="/lobby",
                   responses={500: {
                       "model": ErrorResponse
                   }})

logger = getLogger(__name__)


@router.websocket("/queue-in")
async def queue_in(websocket: WebSocket,
                   queue_in_type: Annotated[QueueInType,
                                            Query(default=QueueInType.NEW)],
                   prev_game_id: Annotated[int | None, Query()],
                   service: QueueInService = Depends()):
    """
    [Game mode: Random]
    This endpoint is reponsible for sending lobby related events to users.
    """
    try:
        await websocket.accept()
        await service.queue_in(websocket=websocket,
                               queue_in_type=queue_in_type,
                               prev_game_id=prev_game_id)
    except Exception as ex:
        logger.exception("something whent wrong")
        await websocket.close(reason=str(ex))


@router.get("/info/random")
async def info_random():
    ...


@router.post("/leave")
async def leave():
    ...


@router.get("/countdown")
async def countdown():
    ...


@router.post("/start")
async def start():
    # TODO
    ...
