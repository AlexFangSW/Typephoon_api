from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, RedirectResponse

from typephoon_api.types.errors import TokenNotProvided

from ..lib.dependencies import (
    access_cookie,
    get_auth_service,
    get_auth_service_with_provider,
    get_setting,
    refresh_cookie,
)
from ..lib.util import catch_error_async
from ..services.auth import AuthService
from ..types.enums import CookieNames, ErrorCode
from ..types.responses.base import ErrorResponse, SuccessResponse
from ..types.setting import Setting

router = APIRouter(tags=["Auth"], prefix="/auth")


@router.get("/{provider}/login")
@catch_error_async
async def login(
    setting: Setting = Depends(get_setting),
    service: AuthService = Depends(get_auth_service_with_provider),
):
    """
    Set perams and redirect users to the login page
    """
    ret = await service.login()

    if not ret.ok:
        return RedirectResponse(setting.error_redirect)

    assert ret.data is not None
    return RedirectResponse(ret.data)


@router.get("/{provider}/login-redirect")
@catch_error_async
async def login_redirect(
    state: str,
    code: str,
    setting: Setting = Depends(get_setting),
    service: AuthService = Depends(get_auth_service_with_provider),
):
    ret = await service.login_redirect(state, code)

    if not ret.ok:
        return RedirectResponse(setting.error_redirect)

    assert ret.data is not None

    response = RedirectResponse(ret.data.url)
    response.set_cookie(
        CookieNames.ACCESS_TOKEN,
        ret.data.access_token,
        path="/",
        max_age=setting.token.refresh_duration,
        httponly=True,
        secure=True,
    )
    response.set_cookie(
        CookieNames.REFRESH_TOKEN,
        ret.data.refresh_token,
        path=ret.data.refresh_endpoint,
        max_age=setting.token.refresh_duration,
        httponly=True,
        secure=True,
    )
    response.set_cookie(
        CookieNames.USERNAME,
        quote(ret.data.username),
        path="/",
        max_age=setting.token.refresh_duration,
        httponly=True,
        secure=True,
    )

    return response


@router.post("/logout", responses={200: {"model": SuccessResponse}})
@catch_error_async
async def logout(
    access_token: str | None = Depends(access_cookie),
    service: AuthService = Depends(get_auth_service),
    setting: Setting = Depends(get_setting),
):
    if access_token:
        ret = await service.logout(access_token=access_token)
        assert ret.ok

    msg = jsonable_encoder(SuccessResponse())
    response = JSONResponse(msg, status_code=200)

    response.delete_cookie(CookieNames.ACCESS_TOKEN)
    response.delete_cookie(
        CookieNames.REFRESH_TOKEN, path=setting.token.refresh_endpoint
    )
    response.delete_cookie(CookieNames.USERNAME)

    return response


@router.post(
    "/token-refresh",
    responses={
        200: {"model": SuccessResponse},
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
@catch_error_async
async def token_refresh(
    refresh_token: str | None = Depends(refresh_cookie),
    setting: Setting = Depends(get_setting),
    service: AuthService = Depends(get_auth_service),
):
    if refresh_token is None:
        raise TokenNotProvided(
            f"Refresh token {CookieNames.REFRESH_TOKEN} not present in cookie"
        )

    ret = await service.token_refresh(refresh_token)

    if not ret.ok:
        assert ret.error
        if ret.error.code in {
            ErrorCode.REFRESH_TOKEN_MISSMATCH,
            ErrorCode.INVALID_TOKEN,
        }:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=400)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data is not None
    msg = jsonable_encoder(SuccessResponse())
    response = JSONResponse(msg, status_code=200)
    response.set_cookie(
        CookieNames.ACCESS_TOKEN,
        ret.data,
        path="/",
        max_age=setting.token.refresh_duration,
        httponly=True,
        secure=True,
    )
    return response


@router.get(
    "/guest-token",
    responses={200: {"model": SuccessResponse}, 400: {"model": ErrorResponse}},
)
@catch_error_async
async def get_guest_token(
    key: str,
    setting: Setting = Depends(get_setting),
    service: AuthService = Depends(get_auth_service),
):
    ret = await service.get_guest_token(key)
    if not ret.ok:
        assert ret.error is not None
        if ret.error.code == ErrorCode.KEY_NOT_FOUND:
            msg = jsonable_encoder(ErrorResponse(error=ret.error))
            return JSONResponse(msg, status_code=400)
        else:
            raise ValueError(f"unknown error code: {ret.error.code}")

    assert ret.data is not None
    msg = jsonable_encoder(SuccessResponse())
    response = JSONResponse(msg, status_code=200)
    response.set_cookie(
        CookieNames.ACCESS_TOKEN,
        ret.data,
        path="/",
        max_age=setting.token.refresh_duration,
        httponly=True,
        secure=True,
    )
    return response
