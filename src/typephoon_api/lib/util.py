from functools import wraps
from logging import getLogger
from logging.config import dictConfig
from typing import Callable
from alembic import command
from alembic.config import Config
from fastapi.responses import JSONResponse
from pydantic_core import Url

from ..types.log import TRACE
from ..types.setting import Setting

from ..types.responses.base import ErrorContent, ErrorResponse

logger = getLogger(__name__)


def sanitized_dsn(dsn: str) -> Url:
    temp_url = Url(dsn)
    assert temp_url.host
    assert temp_url.path
    url = Url.build(scheme=temp_url.scheme,
                    username=temp_url.username,
                    password="***",
                    host=temp_url.host,
                    port=temp_url.port,
                    path=temp_url.path.lstrip("/"))
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


def load_setting(path: str) -> Setting:
    with open(path, "r") as file:
        return Setting.model_validate_json(file.read())


def catch_error_sync(func: Callable):

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            logger.exception("something went wrong")
            error = ErrorContent(message=str(ex))
            msg = ErrorResponse(error=error).model_dump()
            return JSONResponse(msg, status_code=500)

    return wrapped


def catch_error_async(func: Callable):

    @wraps(func)
    async def wrapped(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as ex:
            logger.exception("something went wrong")
            error = ErrorContent(message=str(ex))
            msg = ErrorResponse(error=error).model_dump()
            return JSONResponse(msg, status_code=500)

    return wrapped


def get_state_key(inpt: str) -> str:
    return f"login_state-{inpt}"
