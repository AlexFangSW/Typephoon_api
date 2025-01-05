from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..types.responses.lobby import LobbyPlayersResponse

from ..types.jwt import JWTPayload

from ..services.lobby import LobbyService

from ..services.queue_in import QueueInService

from ..types.responses.base import ErrorResponse, SuccessResponse

from ..types.enums import QueueInType

from ..lib.dependencies import get_access_token_info, get_lobby_service, get_queue_in_service

from ..lib.util import catch_error_async

router = APIRouter(tags=["Lobby"],
                   prefix="/lobby",
                   responses={
                       500: {
                           "model": ErrorResponse
                       },
                       400: {
                           "model": ErrorResponse
                       }
                   })

logger = getLogger(__name__)


@router.websocket("/queue-in")
async def queue_in(websocket: WebSocket,
                   queue_in_type: Annotated[QueueInType,
                                            Query(default=QueueInType.NEW)],
                   prev_game_id: Annotated[int | None, Query()],
                   service: QueueInService = Depends(get_queue_in_service)):
    """
    [Game mode: Multi]
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


@router.get("/players")
@catch_error_async
async def players(game_id: int,
                  current_user: JWTPayload = Depends(get_access_token_info),
                  service: LobbyService = Depends(get_lobby_service)):

    ret = await service.get_players(user_id=current_user.sub, game_id=game_id)

    assert ret.ok
    assert ret.data

    msg = jsonable_encoder(
        LobbyPlayersResponse(me=ret.data.me, others=ret.data.others))
    return JSONResponse(msg, status_code=200)


@router.post("/leave")
async def leave(game_id: int,
                current_user: JWTPayload = Depends(get_access_token_info),
                service: LobbyService = Depends(get_lobby_service)):

    ret = await service.leave(user_id=current_user.sub, game_id=game_id)

    assert ret.ok
    msg = jsonable_encoder(SuccessResponse())
    return JSONResponse(msg, status_code=200)


@router.get("/countdown")
async def countdown():
    """
    lobby countdown in seconds
    """
    ...
