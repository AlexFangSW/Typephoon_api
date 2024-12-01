from logging import getLogger
from logging.config import dictConfig
from alembic import command
from alembic.config import Config

from ..types.setting import TRACE, Setting

logger = getLogger(__name__)


def db_migration(setting: Setting):
    logger.info("running migration, DSN: %s", setting.db.dsn)
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
