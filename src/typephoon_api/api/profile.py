from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from ..types.responses.profile import (
    ProfileGraphResponse,
    ProfileHistoryItem,
    ProfileHistoryResponse,
    ProfileStatisticsResponse,
)

from ..types.errors import InvalidCookieToken

from ..types.responses.lobby import LobbyCountdownResponse, LobbyPlayersResponse

from ..services.lobby import LobbyService

from ..services.queue_in import QueueInService

from ..types.responses.base import ErrorResponse, SuccessResponse

from ..types.enums import ErrorCode, QueueInType

from ..lib.dependencies import (
    GetAccessTokenInfoRet,
    get_access_token_info,
    get_lobby_service,
    get_queue_in_service,
)

from ..lib.util import catch_error_async

logger = getLogger(__name__)

router = APIRouter(
    tags=["Profile"],
    prefix="/profile",
    responses={500: {"model": ErrorResponse}},
)


@router.get(
    "/statistics",
    responses={200: {"model": ProfileStatisticsResponse}},
)
@catch_error_async
async def statistics(): ...


@router.get(
    "/graph",
    responses={200: {"model": ProfileGraphResponse}},
)
@catch_error_async
async def graph(): ...


@router.get(
    "/history",
    responses={200: {"model": ProfileHistoryResponse}},
)
@catch_error_async
async def history(): ...
