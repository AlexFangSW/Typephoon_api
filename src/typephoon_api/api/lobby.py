from typing import Annotated
from fastapi import APIRouter, Cookie, Depends, WebSocket
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse

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
async def queue_in(
    websocket: WebSocket,
    setting: Setting = Depends(get_setting),
    service: AuthService = Depends(get_auth_service_with_provider)):
    """
    This endpoint is reponsible for sending lobby related events to users.

    -   Generate temp auth cookies for guests, just for identifiying who they are
        in latter stages. Users will recive an event though this websocket that 
        guides them to request their cookies though an endpoint.
    -   Match making. Tigger update when new team is found.
    -   Trigger update when new user comes in
    -   Trigger game start
        -   When contdown ends 
        -   When all users click 'just start'
    """

    ret = await service.login()

    if not ret.ok:
        return RedirectResponse(setting.error_redirect)

    assert ret.data
    return RedirectResponse(ret.data)
