from logging import getLogger
from typing import Annotated
from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from ..services.profile import ProfileService
from ..types.responses.profile import (
    ProfileGraphResponse,
    ProfileHistoryResponse,
    ProfileStatisticsResponse,
)
from ..types.errors import InvalidCookieToken
from ..types.responses.base import ErrorResponse
from ..lib.dependencies import (
    GetAccessTokenInfoRet,
    get_access_token_info,
    get_profile_service,
)
from ..lib.util import catch_error_async

logger = getLogger(__name__)

router = APIRouter(tags=["Profile"], prefix="/profile")


@router.get(
    "/statistics",
    responses={
        200: {"model": ProfileStatisticsResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
@catch_error_async
async def statistics(
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: ProfileService = Depends(get_profile_service),
):
    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.statistics(
        user_id=current_user.payload.sub, user_type=current_user.payload.user_type
    )

    assert ret.data
    msg = jsonable_encoder(
        ProfileStatisticsResponse(
            best=ret.data.best, last_10=ret.data.last_10, average=ret.data.average
        )
    )
    return JSONResponse(msg, status_code=200)


@router.get(
    "/graph",
    responses={
        200: {"model": ProfileGraphResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
@catch_error_async
async def graph(
    size: Annotated[int, Query(ge=0, le=1000)] = 10,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: ProfileService = Depends(get_profile_service),
):
    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.graph(
        user_id=current_user.payload.sub,
        user_type=current_user.payload.user_type,
        size=size,
    )

    assert ret.data
    msg = jsonable_encoder(ProfileGraphResponse(data=ret.data))
    return JSONResponse(msg, status_code=200)


@router.get(
    "/history",
    responses={
        200: {"model": ProfileHistoryResponse},
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
    },
)
@catch_error_async
async def history(
    page: Annotated[int, Query(gt=0)] = 1,
    size: Annotated[int, Query(ge=0, le=200)] = 50,
    current_user: GetAccessTokenInfoRet = Depends(get_access_token_info),
    service: ProfileService = Depends(get_profile_service),
):
    if current_user.error:
        raise InvalidCookieToken(current_user.error)

    assert current_user.payload
    ret = await service.history(
        user_id=current_user.payload.sub,
        user_type=current_user.payload.user_type,
        size=size,
        page=page,
    )

    assert ret.data
    msg = jsonable_encoder(
        ProfileHistoryResponse(
            total=ret.data.total,
            has_prev_page=ret.data.has_prev_page,
            has_next_page=ret.data.has_next_page,
            data=ret.data.data,
        )
    )
    return JSONResponse(msg, status_code=200)
