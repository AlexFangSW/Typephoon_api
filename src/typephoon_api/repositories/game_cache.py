from contextlib import asynccontextmanager
from datetime import datetime
from logging import getLogger
from redis.asyncio import Redis
from enum import StrEnum
import json

from ..types.common import GameUserInfo

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

    async def get_players(self, game_id: int) -> dict[str, GameUserInfo] | None:
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.PLAYERS)
        ret = await self._redis_conn.get(key)
        if not ret:
            logger.warning("cache not found, game_id: %s", game_id)
            return

        data: dict = json.loads(ret)
        result: dict[str, GameUserInfo] = {}
        for user_id, user_info in data.items():
            result[user_id] = GameUserInfo.model_validate(user_info)

        return result

    async def get_start_time(self, game_id: int) -> datetime | None:
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.COUNTDOWN)
        ret: bytes = await self._redis_conn.get(key)
        if not ret:
            logger.warning("cache not found, game_id: %s", game_id)
            return

        data = ret.decode()
        return datetime.fromisoformat(data)

    async def populate_with_lobby_cache(self,
                                        game_id: int,
                                        lobby_cache_repo: LobbyCacheRepo,
                                        auto_clean: bool = False):
        """
        - auto_clean: clean up lobby cache after populating game cache
        """
        # player cache
        lobby_players = await lobby_cache_repo.get_players(game_id)
        if lobby_players:
            game_players: dict[str, dict] = {}

            for user_id, user_info in lobby_players.items():
                game_players[user_id] = GameUserInfo.from_lobby_cache(
                    user_info).model_dump()

            player_key = self._gen_cache_key(game_id=game_id,
                                             cache_type=GameCacheType.PLAYERS)
            await self._redis_conn.set(
                name=player_key,
                value=json.dumps(game_players),
                ex=self._setting.redis.in_game_cache_expire_time)

        else:
            logger.warning("lobby player cache not found")

        # countdown cache
        lobby_start_time = await lobby_cache_repo.get_start_time(game_id)
        if lobby_start_time:
            start_time_key = self._gen_cache_key(
                game_id=game_id, cache_type=GameCacheType.COUNTDOWN)
            await self._redis_conn.set(
                name=start_time_key,
                value=lobby_start_time.isoformat(),
                ex=self._setting.redis.in_game_cache_expire_time)
        else:
            logger.warning("lobby start time cache not found")

        if auto_clean:
            await lobby_cache_repo.clear_cache(game_id)
