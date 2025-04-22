from __future__ import annotations

from datetime import timedelta
from logging import getLogger
from os import getenv
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_NAME = getenv("SERVER_NAME", None)
LOG_LEVEL = getenv("LOG_LEVEL", "INFO")

logger = getLogger(__name__)


def default_logger() -> dict:
    return {
        "disable_existing_loggers": False,
        "version": 1,
        "handlers": {
            "default": {"class": "logging.StreamHandler", "formatter": "default"}
        },
        "formatters": {
            "default": {
                "format": "%(levelname)s %(name)s:%(funcName)s:%(lineno)d :: %(message)s"
            }
        },
        "root": {"level": "INFO", "handlers": ["default"]},
        "loggers": {"typephoon_api": {"level": LOG_LEVEL}},
    }


class DBSetting(BaseModel):
    username: str = "user"
    password: str = "password"
    host: str = "localhost"
    port: int = 5432
    db: str = "typephoon"
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
    in_game_cache_expire_time: int = 60 * 15
    result_cache_expire_time: int = 60 * 15


class CORSSetting(BaseModel):
    allow_origins: list[str] = Field(default_factory=list)


class ServerSetting(BaseModel):
    port: int = 8080


class TokenSetting(BaseModel):
    """
    JWT token
    - Token public / private keys
    - access_duration: (seconds)
        - duration for the access token
    - refresh_duration: (seconds)
        - duration for the refresh token
    """

    public_key: str = ""
    private_key: str = ""
    refresh_endpoint: str = "/api/v1/auth/token-refresh"
    access_duration: int = int(timedelta(minutes=15).total_seconds())
    refresh_duration: int = int(timedelta(days=30).total_seconds())


class GoogleSetting(BaseModel):
    client_id: str = ""
    client_secret: str = ""
    redirect_url: str = "http://localhost:8080/api/v1/auth/login-redirect"


class AMQPSetting(BaseModel):
    user: str = "guest"
    password: str = "guest"
    host: str = "localhost"
    vhost: str = "typephoon"
    prefetch_count: int = 50

    # exchanges
    lobby_notify_fanout_exchange: str = "lobby.notify"
    lobby_countdown_direct_exchange: str = "lobby.countdown"
    game_keystroke_fanout_exchange: str = "game.keystroke"
    game_cleanup_direct_exchange: str = "game.cleanup"
    game_start_fanout_exchange: str = "game.start"

    # queues with consumers
    lobby_notify_queue: str = "lobby.notify"
    lobby_notify_queue_routing_key: str = "lobby.notify"

    lobby_countdown_queue: str = "lobby.countdown"
    lobby_countdown_queue_routing_key: str = "lobby.countdown"

    game_keystroke_queue: str = "game.keystroke"

    game_start_queue: str = "game.start"
    game_start_queue_routing_key: str = "game.start"

    game_cleanup_queue: str = "game.cleanup"
    game_cleanup_queue_routing_key: str = "game.cleanup"

    # "wait queues" use deadletter policies to connect with exchanges.
    # no consumers, publish only.
    lobby_multi_countdown_wait_queue: str = "lobby.multi.countdown.wait"
    game_start_wait_queue: str = "game.start.wait"
    game_cleanup_wait_queue: str = "game.cleanup.wait"

    def model_post_init(self, _: Any) -> None:
        # if there are multiple servers, each server needs to have a unique SERVER_NAME
        if SERVER_NAME:
            self.lobby_notify_queue = f"{self.lobby_notify_queue}.{SERVER_NAME}"
            self.game_keystroke_queue = f"{self.game_keystroke_queue}.{SERVER_NAME}"
            self.game_start_queue = f"{self.game_start_queue}.{SERVER_NAME}"


class GameSetting(BaseModel):
    """
    Attributes:
    - start_countdown: seconds
    - lobby_countdown: seconds
    - cleanup_countdown: seconds
    """

    start_countdown: int = 5
    lobby_countdown: int = 5
    player_limit: int = 5
    cleanup_countdown: int = 60 * 15
    word_file: str = "./data/words.txt"


class Setting(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TP_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    db: DBSetting = Field(default_factory=DBSetting)
    redis: RedisSetting = Field(default_factory=RedisSetting)
    cors: CORSSetting = Field(default_factory=CORSSetting)
    server: ServerSetting = Field(default_factory=ServerSetting)
    logger: dict = Field(default_factory=default_logger)
    google: GoogleSetting = Field(default_factory=GoogleSetting)
    token: TokenSetting = Field(default_factory=TokenSetting)
    amqp: AMQPSetting = Field(default_factory=AMQPSetting)
    game: GameSetting = Field(default_factory=GameSetting)

    front_end_endpoint: str = "http://localhost:3000"
    error_redirect: str = "http://localhost:3000/error"

    server_name: str | None = SERVER_NAME

    @classmethod
    def from_file(cls, base: str = "setting.yaml") -> Self:
        base_file = Path(base)
        if base_file.exists():
            with base_file.open("r") as f:
                loaded = yaml.safe_load(f)
                base_setting = cls.model_validate(loaded)
        else:
            logger.warning("base setting file not found at: %s, using default.", base)
            base_setting = cls()

        return base_setting


if __name__ == "__main__":
    print(yaml.safe_dump(Setting().model_dump()))
