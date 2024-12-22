from datetime import timedelta
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
    host: str = "localhost"
    port: int = 5432
    db: str = "db"
    username: str = "user"
    password: str = "password"

    pool_size: int = 5
    echo: bool = False

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"


class RedisSetting(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    expire_time: int = 60


class CORSSetting(BaseModel):
    allow_origins: list[str] = Field(default_factory=list)


class ServerSetting(BaseModel):
    port: int = 8080


class TokenSetting(BaseModel):
    """
    JWT token
    - access_duration: (seconds)
        - duration for the access token
    - refresh_duration: (seconds)
        - duration for the refresh token
    """
    public_key: str = ""
    private_key: str = ""
    refresh_endpoint: str = "/api/v1/auth/token_refresh"
    access_duration: int = int(timedelta(minutes=5).total_seconds())
    refresh_duration: int = int(timedelta(days=30).total_seconds())


class GoogleSetting(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_url: str = "http://localhost:8080/api/v1/auth/login-redirect"


class Setting(BaseModel):
    db: DBSetting = Field(default_factory=DBSetting)
    redis: RedisSetting = Field(default_factory=RedisSetting)
    cors: CORSSetting = Field(default_factory=CORSSetting)
    server: ServerSetting = Field(default_factory=ServerSetting)
    logger: dict = Field(default_factory=default_logger)
    google: GoogleSetting = Field(default_factory=GoogleSetting)
    token: TokenSetting = Field(default_factory=TokenSetting)

    front_end_endpoint: str = "http://localhost:3000"
    error_redirect: str = "http://localhost:3000/error"


if __name__ == "__main__":
    print(Setting().model_dump_json())
