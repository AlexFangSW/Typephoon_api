from logging import getLogger
from logging.config import dictConfig
from alembic import command
from alembic.config import Config
from pydantic_core import Url

from ..types.setting import TRACE, Setting

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
