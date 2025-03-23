from redis.asyncio import Redis
from time import time

from ..types.setting import Setting
from uuid import uuid4


class GuestTokenRepo:
    def __init__(self, redis_conn: Redis, setting: Setting) -> None:
        self._redis_conn = redis_conn
        self._setting = setting

    def _gen_token_key(self) -> str:
        ts_part = int(time() * 1000)
        uuid_part = uuid4().hex.split("-")[0]
        return f"guest-token-{uuid_part}-{ts_part}"

    async def store(self, token: str) -> str:
        """gen random key and store it in redis"""
        key = self._gen_token_key()
        await self._redis_conn.set(
            name=key, value=token, ex=self._setting.redis.expire_time, nx=True
        )
        return key

    async def get(self, key: str) -> str | None:
        ret: bytes | None = await self._redis_conn.getdel(key)
        if ret is not None:
            return ret.decode()
