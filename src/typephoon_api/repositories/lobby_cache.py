from contextlib import asynccontextmanager
from datetime import datetime
from logging import getLogger
from redis.asyncio import Redis
import json
from enum import StrEnum

from ..types.setting import Setting
from ..types.common import LobbyUserInfo

logger = getLogger(__name__)


class LobbyCacheType(StrEnum):
    PLAYERS = "players"
    COUNTDOWN = "countdown"


class LobbyCacheRepo:
    def __init__(self, redis_conn: Redis, setting: Setting) -> None:
        self._redis_conn = redis_conn
        self._setting = setting

    def _gen_cache_key(self, game_id: int, cache_type: LobbyCacheType) -> str:
        return f"lobby-cache-{cache_type}-{game_id}"

    def _gen_lock_key(self, game_id: str) -> str:
        return f"lobby-cache-{game_id}-lock"

    @asynccontextmanager
    async def lock(self, game_id: int):
        lock_key = self._gen_lock_key(str(game_id))
        lock = self._redis_conn.lock(name=lock_key)
        yield lock

    async def add_player(self, game_id: int, user_info: LobbyUserInfo) -> bool:
        """
        player cache is a dict of 'LobbyUserInfo'

        ```json
        {
            "USER_ID": LobbyUserInfo,
            "USER_ID": LobbyUserInfo,
            ...
        }
        ```
        """
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.PLAYERS)
        new_player = False

        # get current status
        ret: bytes | None = await self._redis_conn.get(name=key)
        if ret is not None:
            current_status = json.loads(ret)
        else:
            current_status = {}

        if user_info.id not in current_status:
            new_player = True

        # set new status
        current_status[user_info.id] = user_info.model_dump()
        await self._redis_conn.set(
            name=key,
            value=json.dumps(current_status),
            ex=self._setting.redis.expire_time,
        )
        return new_player

    async def is_new_player(self, game_id: int, user_id: str) -> bool:
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.PLAYERS)
        new_player = False
        ret = await self._redis_conn.get(name=key)

        if ret:
            current_status = json.loads(ret)
        else:
            current_status = {}

        if user_id not in current_status:
            new_player = True

        return new_player

    async def touch_cache(self, game_id: int, ex: int):
        """
        Update the expire time
        """
        player_key = self._gen_cache_key(
            game_id=game_id, cache_type=LobbyCacheType.PLAYERS
        )
        countdown_key = self._gen_cache_key(
            game_id=game_id, cache_type=LobbyCacheType.COUNTDOWN
        )
        pipeline = self._redis_conn.pipeline()
        pipeline.expire(player_key, time=ex)
        pipeline.expire(countdown_key, time=ex)
        await pipeline.execute()

    async def set_start_time(self, game_id: int, start_time: datetime):
        """
        Set start time for countdown pooling
        """
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.COUNTDOWN)

        await self._redis_conn.set(
            name=key, value=start_time.isoformat(), ex=self._setting.redis.expire_time
        )

    async def get_start_time(self, game_id: int) -> datetime | None:
        """
        Get start time for countdown pooling
        """
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.COUNTDOWN)

        ret: bytes | None = await self._redis_conn.get(name=key)
        if ret is None:
            logger.warning("game not found, game_id: %s", game_id)
            return

        return datetime.fromisoformat(ret.decode())

    async def clear_cache(self, game_id: int):
        """
        Clear all cache for the game
        """
        player_cache_key = self._gen_cache_key(
            game_id=game_id, cache_type=LobbyCacheType.PLAYERS
        )
        countdown_cache_key = self._gen_cache_key(
            game_id=game_id, cache_type=LobbyCacheType.COUNTDOWN
        )

        await self._redis_conn.delete(player_cache_key, countdown_cache_key)

    async def remove_player(self, game_id: int, user_id: str) -> bool:
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.PLAYERS)
        ret: bytes | None = await self._redis_conn.get(name=key)
        if ret is None:
            logger.warning("game not found, game_id: %s", game_id)
            return False

        data: dict = json.loads(ret)
        exist = data.pop(user_id)
        await self._redis_conn.set(
            name=key, value=json.dumps(data), ex=self._setting.redis.expire_time
        )
        return True if exist is not None else False

    async def get_players(self, game_id: int) -> dict[str, LobbyUserInfo] | None:
        key = self._gen_cache_key(game_id=game_id, cache_type=LobbyCacheType.PLAYERS)
        ret: bytes | None = await self._redis_conn.get(name=key)
        if ret is None:
            logger.warning("game not found, game_id: %s", game_id)
            return

        raw: dict = json.loads(ret)
        result: dict[str, LobbyUserInfo] = {
            k: LobbyUserInfo.model_validate(v) for k, v in raw.items()
        }
        return result
