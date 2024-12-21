from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse

from ..lib.dependencies import get_auth_service
from ..services.auth import AuthService

from ..lib.util import catch_error_async

router = APIRouter(tags=["Auth"], prefix="/auth")


@router.get("/login")
@catch_error_async
async def login(service: AuthService = Depends(get_auth_service)):
    """
    Set perams and redirect users to the login page
    """
    ret = await service.login()
    assert ret.data
    return RedirectResponse(ret.data)


# TODO add query perams
@router.get("/login-redirect")
@catch_error_async
async def login_redirect(service: AuthService = Depends(get_auth_service)):
    ...


@router.post("/logout")
@catch_error_async
async def logout(service: AuthService = Depends(get_auth_service)):
    ...


@router.post("/token/refresh")
@catch_error_async
async def token_refresh(service: AuthService = Depends(get_auth_service)):
    ...
