from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.util import await_only

from ..services.lobby_random import LobbyRandomService

from ..types.setting import Setting

from ..types.responses.base import ErrorResponse, SuccessResponse

from ..types.enums import CookieNames, ErrorCode

from ..lib.dependencies import get_auth_service, get_auth_service_with_provider, get_setting
from ..services.auth import AuthService

from ..lib.util import catch_error_async

router = APIRouter(tags=["Lobby"],
                   prefix="/lobby",
                   responses={500: {
                       "model": ErrorResponse
                   }})


@router.websocket("/queue-in")
@catch_error_async
async def queue_in(websocket: WebSocket,
                   service: LobbyRandomService = Depends()):
    """
    [Game mode: Random]
    This endpoint is reponsible for sending lobby related events to users.
    """
    await service.queue_in(websocket)
