from datetime import datetime

from redis.asyncio import Redis

from ..types.setting import Setting
from ..types.common import LobbyUserInfo


class GameCacheRepo:

    def __init__(self, redis_conn: Redis, setting: Setting) -> None:
        self._redis_conn = redis_conn
        self._setting = setting

    def _gen_cache_key(self, id: int) -> str:
        return f"game-cache-{id}"

    async def add_player(self, id: int, user_info: LobbyUserInfo):
        ...

    async def set_start_time(self, id: int, start_time: datetime):
        ...

    ...
