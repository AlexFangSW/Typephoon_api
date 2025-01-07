from contextlib import asynccontextmanager
from logging import getLogger
from redis.asyncio import Redis
from enum import StrEnum

from .lobby_cache import LobbyCacheRepo

from ..types.setting import Setting

logger = getLogger(__name__)


class GameCacheType(StrEnum):
    PLAYERS = "players"
    COUNTDOWN = "countdown"


class GameCacheRepo:

    def __init__(self, redis_conn: Redis, setting: Setting) -> None:
        self._redis_conn = redis_conn
        self._setting = setting

    def _gen_cache_key(self, game_id: int, cache_type: GameCacheType) -> str:
        return f"game-cache-{cache_type}-{game_id}"

    def _gen_lock_key(self, game_id: str) -> str:
        return f"game-cache-{game_id}-lock"

    @asynccontextmanager
    async def lock(self, game_id: int):
        lock_key = self._gen_lock_key(str(game_id))
        lock = self._redis_conn.lock(name=lock_key)
        yield lock

    # TODO
    async def populate_with_lobby_cache(self, game_id: int,
                                        lobby_cache_repo: LobbyCacheRepo):
        ...
