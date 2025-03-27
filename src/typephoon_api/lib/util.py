import json
from dataclasses import dataclass
from functools import wraps
from hashlib import md5
from logging import getLogger
from logging.config import dictConfig
from typing import Callable
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.responses import JSONResponse
from pydantic_core import Url

from ..types.common import LobbyUserInfo
from ..types.enums import ErrorCode
from ..types.errors import InvalidCookieToken
from ..types.log import TRACE
from ..types.responses.base import ErrorContext, ErrorResponse
from ..types.setting import Setting
from .oauth_providers.base import OAuthProviders

logger = getLogger(__name__)


def sanitized_dsn(dsn: str) -> Url:
    temp_url = Url(dsn)
    assert temp_url.host
    assert temp_url.path
    url = Url.build(
        scheme=temp_url.scheme,
        username=temp_url.username,
        password="***",
        host=temp_url.host,
        port=temp_url.port,
        path=temp_url.path.lstrip("/"),
    )
    return url


def db_migration(setting: Setting):
    logger.info("running migration on %s", sanitized_dsn(setting.db.dsn))
    config = Config()
    config.set_main_option("script_location", "migration")
    config.set_main_option("sqlalchemy.url", setting.db.dsn)
    command.upgrade(config, "head")
    logger.info("finish migration")


def init_logger(setting: Setting):
    dictConfig(setting.logger)
    logger.info("logger initialized")
    logger.debug("debug level activated")
    logger.log(TRACE, "trace level activated")


def load_setting(base: str, secret: str) -> Setting:
    return Setting.from_file(base, secret)


def catch_error_sync(func: Callable):
    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            logger.exception("something went wrong")
            error = ErrorContext(message=str(ex))
            msg = ErrorResponse(error=error).model_dump()
            return JSONResponse(msg, status_code=500)

    return wrapped


def catch_error_async(func: Callable):
    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return await func(*args, **kwargs)

        except InvalidCookieToken as ex:
            logger.warning("token error: %s", str(ex))
            error = ErrorContext(code=ErrorCode.INVALID_TOKEN, message=str(ex))
            msg = ErrorResponse(error=error).model_dump()
            return JSONResponse(msg, status_code=400)

        except Exception:
            logger.exception("something went wrong")
            # error = ErrorContext(message=str(ex))
            msg = ErrorResponse().model_dump()
            return JSONResponse(msg, status_code=500)

    return wrapped


def get_state_key(inpt: str) -> str:
    return f"login_state-{inpt}"


def gen_user_id(base_id: str, provider: OAuthProviders) -> str:
    return f"{provider}-{base_id}"


@dataclass(slots=True)
class GuestUserInfo:
    id: str
    name: str


def gen_guest_user_info() -> LobbyUserInfo:
    id = uuid4().hex
    first_part = id.split("-")[0]
    return LobbyUserInfo(id=f"guest-{id}", name=f"guest-{first_part}")


def get_dict_hash(inpt: dict) -> str:
    """
    This is only used to check if the content of the input is identical
    """
    return md5(json.dumps(inpt).encode()).hexdigest()[:8]
