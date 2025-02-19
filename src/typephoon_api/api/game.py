from logging import getLogger
from fastapi import APIRouter, Depends, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..types.errors import InvalidCookieToken

from ..lib.util import catch_error_async

from ..lib.dependencies import (
    GetAccessTokenInfoRet,
    get_access_token_info,
    get_game_event_service,
    get_game_service,
)

from ..services.game import GameService

from ..services.game_event import GameEventService

from ..types.requests.game import GameStatistics

from ..types.responses.game import (
    GameCountdownResponse,
    GameResultResponse,
    GameWordsResponse,
)

from ..types.enums import ErrorCode

from ..types.responses.base import ErrorResponse, SuccessResponse

logger = getLogger(__name__)

router = APIRouter(tags=["Game"], prefix="/game")


@router.websocket("/ws")
async def ws(
    websocket: WebSocket,
    game_id: int,
    service: GameEventService = Depends(get_game_event_service),
):
    """
    - send and recive each key stroke
    """
    try:
        bg = await service.subscribe(websocket=websocket, game_id=game_id)
        if bg is not None:
            await service.close_wait(bg)
    except Exception as ex:
        logger.exception("something went wrong")
        await websocket.close(reason=str(ex))


@router.get(
    "/countdown",
    responses={200: {"model": GameCountdownResponse}, 400: {"model": ErrorResponse}},
)
@catch_error_async
async def countdown(game_id: int, service: GameService = Depends(get_game_service)):
    """
    game countdown in seconds
    """
    ret = await service.get_countdown(game_id)

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data is not None
    msg = jsonable_encoder(GameCountdownResponse(seconds_left=ret.data))
    return JSONResponse(msg, status_code=200)


@router.post(
    "/statistics",
    responses={200: {"model": SuccessResponse}, 400: {"model": ErrorResponse}},
)
@catch_error_async
async def write_statistics(
    statistics: GameStatistics,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: GameService = Depends(get_game_service),
):
    """
    on finish, users will send their statistics to the server
    - WPM, ACC ... etc
    - The ranking will be decided here by the server
    """
    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.write_statistics(
        statistics=statistics,
        username=current_user.payload.name,
        user_type=current_user.payload.user_type,
        user_id=current_user.payload.sub,
    )

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=400)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    msg = jsonable_encoder(SuccessResponse())
    return JSONResponse(msg, status_code=200)


@router.get(
    "/statistics",
    responses={200: {"model": GameResultResponse}, 404: {"model": ErrorResponse}},
)
@catch_error_async
async def result(game_id: int, service: GameService = Depends(get_game_service)):
    """
    information for the result of this game
    - ranking, wpm, acc ... etc
    """
    ret = await service.get_result(game_id)

    if not ret.ok:
        assert ret.error
        if ret.error.code == ErrorCode.GAME_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data is not None
    msg = jsonable_encoder(GameResultResponse(ranking=ret.data.ranking))
    return JSONResponse(msg, status_code=200)


@router.get(
    "/words",
    responses={200: {"model": GameWordsResponse}, 404: {"model": ErrorResponse}},
)
@catch_error_async
async def words(
    game_id: int,
    service: GameService = Depends(get_game_service),
):
    """
    Get words for this game
    """
    ret = await service.get_words(game_id=game_id)
    if not ret.ok:
        assert ret.error
        if ret.error.code in {ErrorCode.GAME_NOT_FOUND, ErrorCode.WORDS_NOT_FOUND}:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=404)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data is not None
    msg = jsonable_encoder(GameWordsResponse(words=ret.data))
    return JSONResponse(msg, status_code=200)
