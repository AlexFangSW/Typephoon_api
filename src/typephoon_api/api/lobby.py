from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..types.errors import InvalidCookieToken

from ..orm.game import GameType

from ..types.responses.lobby import LobbyCountdownResponse, LobbyPlayersResponse

from ..types.jwt import JWTPayload

from ..services.lobby import LobbyService

from ..services.queue_in import QueueInService

from ..types.responses.base import ErrorResponse, SuccessResponse

from ..types.enums import ErrorCode, QueueInType

from ..lib.dependencies import GetAccessTokenInfoRet, get_access_token_info, get_lobby_service, get_queue_in_service

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
                   prev_game_id: Annotated[int | None, Query()],
                   queue_in_type: Annotated[QueueInType,
                                            Query()] = QueueInType.NEW,
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
async def players(
    game_id: int,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: LobbyService = Depends(get_lobby_service)):

    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.get_players(user_id=current_user.payload.sub,
                                    game_id=game_id)

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data
    msg = jsonable_encoder(
        LobbyPlayersResponse(me=ret.data.me, others=ret.data.others))
    return JSONResponse(msg, status_code=200)


@router.post("/leave")
@catch_error_async
async def leave(
    game_id: int,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: LobbyService = Depends(get_lobby_service)):

    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.leave(user_id=current_user.payload.sub, game_id=game_id)

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    msg = jsonable_encoder(SuccessResponse())
    return JSONResponse(msg, status_code=200)


@router.get("/countdown")
@catch_error_async
async def get_countdown(game_id: int,
                        service: LobbyService = Depends(get_lobby_service)):
    """
    lobby countdown in seconds
    """

    ret = await service.get_countdown(game_id=game_id)

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data
    msg = jsonable_encoder(LobbyCountdownResponse(seconds_left=ret.data))
    return JSONResponse(msg, status_code=200)
