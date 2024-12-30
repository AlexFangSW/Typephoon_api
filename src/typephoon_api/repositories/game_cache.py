from dataclasses import asdict
from datetime import datetime
from redis.asyncio import Redis
import json
from enum import StrEnum
from ..types.setting import Setting
from ..types.common import LobbyUserInfo


class GameCacheType(StrEnum):
    PLAYERS = "players"
    COUNTDOWN = "countdown"


class GameCacheRepo:

    def __init__(self, redis_conn: Redis, setting: Setting) -> None:
        self._redis_conn = redis_conn
        self._setting = setting

    def _gen_cache_key(self, game_id: int, cache_type: GameCacheType) -> str:
        return f"game-cache-{cache_type}-{game_id}"

    def _gen_lock_key(self, key: str) -> str:
        return f"{key}-lock"

    async def add_player(self, game_id: int, user_info: LobbyUserInfo) -> bool:
        """
        player is a dict of 'LobbyUserInfo'

        ```json
        {
            "USER_ID": LobbyUserInfo,
            "USER_ID": LobbyUserInfo,
            ...
        }
        ```
        """
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.PLAYERS)
        lock_key = self._gen_lock_key(key)
        lock = self._redis_conn.lock(name=lock_key)

        new_player = False
        async with lock:
            # get current status
            ret = await self._redis_conn.get(name=key)
            if ret:
                current_status = json.loads(ret)
            else:
                current_status = {}

            if user_info.id not in current_status:
                new_player = True

            # set new status
            current_status[user_info.id] = asdict(user_info)
            await self._redis_conn.set(name=key,
                                       value=json.dumps(current_status),
                                       ex=self._setting.redis.expire_time)
        return new_player

    async def is_new_player(self, game_id: int, user_id: str) -> bool:
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.PLAYERS)
        new_player = False
        ret = await self._redis_conn.get(name=key)

        if ret:
            current_status = json.loads(ret)
        else:
            current_status = {}

        if user_id not in current_status:
            new_player = True

        return new_player

    async def touch_player_cache(self, game_id: int, ex: int):
        """
        Update the expire time
        """
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.PLAYERS)
        await self._redis_conn.getex(name=key, ex=ex)

    async def set_start_time(self, game_id: int, start_time: datetime):
        key = self._gen_cache_key(game_id=game_id,
                                  cache_type=GameCacheType.COUNTDOWN)

        await self._redis_conn.set(name=key,
                                   value=start_time.isoformat(),
                                   ex=self._setting.redis.expire_time)
