from pydantic import BaseModel, Field


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


class DBSetting(BaseModel):
    dsn: str = "postgresql://user:pwd@localhost:5432/db"


class CacheSetting(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    expire_time: int = 60


class CORSSetting(BaseModel):
    allow_origins: list[str] = Field(default_factory=list)


class ServerSetting(BaseModel):
    port: int = 8080


class Setting(BaseModel):
    db: DBSetting = Field(default_factory=DBSetting)
    cache: CacheSetting = Field(default_factory=CacheSetting)
    cors: CORSSetting = Field(default_factory=CORSSetting)
    server: ServerSetting = Field(default_factory=ServerSetting)
    logger: dict = Field(default_factory=default_logger)
