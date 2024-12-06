from pydantic import BaseModel, Field


class DBSetting(BaseModel):
    dsn: str = "postgresql://user:pwd@localhost:5432/db"


def default_logger() -> dict:
    return {
        "disable_existing_loggers": False,
        "version": 1,
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default"
            }
        },
        "formatters": {
            "default": {
                "format": "%(levelname)s %(name)s :: %(message)s"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["default"]
        },
        "loggers": {
            "typephoon_api": {
                "level": "INFO"
            }
        }
    }


class Setting(BaseModel):
    db: DBSetting = Field(default_factory=DBSetting)
    logger: dict = Field(default_factory=default_logger)
