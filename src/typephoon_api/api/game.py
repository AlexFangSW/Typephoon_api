from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Depends, Query, WebSocket

from ..lib.util import catch_error_async

from ..lib.dependencies import GetAccessTokenInfoRet, get_access_token_info, get_game_event_service, get_game_service

from ..services.game import GameService

from ..services.game_evnet import GameEventService

from ..types.requests.game import GameStatistics

from ..types.responses.game import GameCountdownResponse, GameResult

from ..types.enums import WSConnectionType

from ..types.responses.base import ErrorResponse

logger = getLogger(__name__)

router = APIRouter(tags=["Game"],
                   prefix="/game",
                   responses={
                       500: {
                           "model": ErrorResponse
                       },
                       400: {
                           "model": ErrorResponse
                       }
                   })


@router.websocket("/ws")
async def ws(websocket: WebSocket,
             prev_game_id: int | None,
             connection_type: Annotated[WSConnectionType,
                                        Query()] = WSConnectionType.NEW,
             service: GameEventService = Depends(get_game_event_service)):
    """
    - send and recive each key stroke
    """
    try:
        ...
    except Exception as ex:
        logger.exception("something went wrong")
        await websocket.close(reason=str(ex))


@router.get("/countdown", responses={200: {"model": GameCountdownResponse}})
@catch_error_async
async def countdown(game_id: int,
                    service: GameService = Depends(get_game_service)):
    """
    game countdown in seconds
    """
    ...


@router.post("/statistics")
@catch_error_async
async def statistics(
    statistics: GameStatistics,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: GameService = Depends(get_game_service)):
    """
    on finish, users will send their statistics to the server
    - WPM, ACC ... etc
    - The ranking will be decided here
    """
    ...


@router.get("/result", responses={200: {"model": GameResult}})
@catch_error_async
async def result(game_id: int,
                 service: GameService = Depends(get_game_service)):
    """
    information for the result of this game
    - ranking, wpm, acc ... etc
    """
    ...
