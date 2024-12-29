from __future__ import annotations
from os import getenv
from typing import Any, Self
from datetime import timedelta
from pydantic import BaseModel, Field
import yaml


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


class DBCredentialsSetting(BaseModel):
    username: str = "user"
    password: str = "password"


class DBSetting(DBCredentialsSetting):
    host: str = "localhost"
    port: int = 5432
    db: str = "db"
    pool_size: int = 5
    echo: bool = False

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"

    @property
    def async_dsn(self) -> str:
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.db}"

    def merge(self, inpt: DBCredentialsSetting):
        self.username = inpt.username
        self.password = inpt.password


class RedisSetting(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    expire_time: int = 60


class CORSSetting(BaseModel):
    allow_origins: list[str] = Field(default_factory=list)


class ServerSetting(BaseModel):
    port: int = 8080


class TokenPK(BaseModel):
    """
    Token public / private keys
    """
    public_key: str = ""
    private_key: str = ""


class TokenSetting(TokenPK):
    """
    JWT token
    - access_duration: (seconds)
        - duration for the access token
    - refresh_duration: (seconds)
        - duration for the refresh token
    """
    refresh_endpoint: str = "/api/v1/auth/token-refresh"
    access_duration: int = int(timedelta(minutes=5).total_seconds())
    refresh_duration: int = int(timedelta(days=30).total_seconds())

    def merge(self, inpt: TokenPK):
        self.public_key = inpt.public_key
        self.private_key = inpt.private_key


class GoogleCredentials(BaseModel):
    client_id: str = ""
    client_secret: str = ""


class GoogleSetting(GoogleCredentials):
    redirect_url: str = "http://localhost:8080/api/v1/auth/login-redirect"

    def merge(self, inpt: GoogleCredentials):
        self.client_secret = inpt.client_secret
        self.client_id = inpt.client_id


class AMQPCredentials(BaseModel):
    user: str = "guest"
    password: str = "guest"


class AMQPSetting(AMQPCredentials):
    host: str = "localhost"
    vhost: str = "typephoon"
    prefetch_count: int = 50

    lobby_notify_fanout_exchange: str = "lobby.notify"
    countdown_direct_exchange: str = "lobby.countdown"

    lobby_notify_queue: str = "lobby.notify"
    lobby_countdown_queue: str = "lobby.countdown"

    lobby_random_countdown_wait_queue: str = "lobby.random.countdown.wait"
    lobby_team_countdown_wait_queue: str = "lobby.team.countdown.wait"

    def merge(self, inpt: AMQPCredentials):
        self.user = inpt.user
        self.password = inpt.password

    def model_post_init(self, _: Any) -> None:
        # if there are multiple servers, each server needs to have a unique SERVER_NAME
        server_name = getenv("SERVER_NAME", "")
        self.lobby_notify_queue = ".".join(
            [self.lobby_notify_queue, server_name])


class SecretSetting(BaseModel):
    google_credential: GoogleCredentials = Field(
        default_factory=GoogleCredentials)
    token_pk: TokenPK = Field(default_factory=TokenPK)
    db: DBCredentialsSetting = Field(default_factory=DBCredentialsSetting)
    amqp: AMQPCredentials = Field(default_factory=AMQPCredentials)


class Setting(BaseModel):
    db: DBSetting = Field(default_factory=DBSetting)
    redis: RedisSetting = Field(default_factory=RedisSetting)
    cors: CORSSetting = Field(default_factory=CORSSetting)
    server: ServerSetting = Field(default_factory=ServerSetting)
    logger: dict = Field(default_factory=default_logger)
    google: GoogleSetting = Field(default_factory=GoogleSetting)
    token: TokenSetting = Field(default_factory=TokenSetting)
    amqp: AMQPSetting = Field(default_factory=AMQPSetting)

    front_end_endpoint: str = "http://localhost:3000"
    error_redirect: str = "http://localhost:3000/error"

    def merge(self, inpt: SecretSetting):
        self.google.merge(inpt.google_credential)
        self.token.merge(inpt.token_pk)
        self.db.merge(inpt.db)
        self.amqp.merge(inpt.amqp)

    @classmethod
    def from_file(cls,
                  base: str = "setting.yaml",
                  secret: str = "setting.secret.yaml") -> Self:

        with open(base, "r") as f:
            loaded = yaml.safe_load(f)
            base_setting = cls.model_validate(loaded)

        with open(secret, "r") as f:
            loaded = yaml.safe_load(f)
            secret_setting = SecretSetting.model_validate(loaded)

        base_setting.merge(secret_setting)

        return base_setting


if __name__ == "__main__":
    print(yaml.safe_dump(Setting().model_dump()))
    print(yaml.safe_dump(SecretSetting().model_dump()))
