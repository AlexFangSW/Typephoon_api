from hashlib import sha256
from logging import getLogger
from os import urandom

from redis.asyncio import Redis

from ..lib.util import get_state_key
from ..types.setting import Setting

logger = getLogger(__name__)


class OAuthStateRepo:
    def __init__(self, setting: Setting, redis_conn: Redis) -> None:
        self._setting = setting
        self._redis_conn = redis_conn

    async def set_state(self) -> str:
        state = sha256(urandom(1024)).hexdigest()
        key = get_state_key(state)
        await self._redis_conn.set(
            key,
            1,
            ex=self._setting.redis.expire_time,
            nx=True,
        )
        return state

    async def state_exist(self, state: str) -> bool:
        key = get_state_key(state)
        exist: bytes | None = await self._redis_conn.getdel(key)

        if exist is None:
            logger.warning("key not found, key: %s", key)
            return False

        return True
