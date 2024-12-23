from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from ..lib.dependencies import get_auth_service
from ..services.auth import AuthService

from ..lib.util import catch_error_async

router = APIRouter(tags=["Auth"], prefix="/auth")


@router.get("/{provider}/login")
@catch_error_async
async def login(service: AuthService = Depends(get_auth_service)):
    """
    Set perams and redirect users to the login page
    """
    ret = await service.login()

    if not ret.ok:
        assert ret.error_redirect_url
        return RedirectResponse(ret.error_redirect_url)

    assert ret.data
    return RedirectResponse(ret.data)


@router.get("/{provider}/login-redirect")
@catch_error_async
async def login_redirect(state: str,
                         code: str,
                         service: AuthService = Depends(get_auth_service)):

    ret = await service.login_redirect(state, code)

    if not ret.ok:
        assert ret.error_redirect_url
        return RedirectResponse(ret.error_redirect_url)

    assert ret.data

    response = RedirectResponse(ret.data.url)
    response.set_cookie("TP_AT",
                        ret.data.access_token,
                        path="/",
                        httponly=True,
                        samesite="strict")
    response.set_cookie("TP_RT",
                        ret.data.refresh_token,
                        path=ret.data.refresh_endpoint,
                        httponly=True,
                        samesite="strict")
    response.set_cookie("USERNAME",
                        ret.data.username,
                        httponly=True,
                        samesite="strict")
    return response


@router.post("/logout")
@catch_error_async
async def logout(service: AuthService = Depends(get_auth_service)):
    ...


@router.post("/token-refresh")
@catch_error_async
async def token_refresh(service: AuthService = Depends(get_auth_service)):
    ...
