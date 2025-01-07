from typing import Annotated
from fastapi import APIRouter, Query, WebSocket

from ..types.enums import WSConnectionType

from ..types.responses.base import ErrorResponse

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
             prev_game_id: Annotated[int | None, Query()],
             connection_type: Annotated[WSConnectionType,
                                        Query()] = WSConnectionType.NEW):
    ...


@router.get("/countdown")
async def countdown():
    """
    game countdown in seconds
    """
    ...


@router.post("/statistics")
async def statistics():
    """
    users will send their statistics to the server when they finish
    - WPM, ACC ... etc
    """

    ...


@router.get("/result")
async def result():
    """
    information for the result of this game
    - ranking, wpm, acc ... etc
    """
    ...
