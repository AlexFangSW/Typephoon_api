from redis.asyncio import Redis


class GuestTokenRepo:

    def __init__(self, redis_conn: Redis) -> None:
        self._redis_conn = redis_conn

    async def store(self, token: str) -> str:
        """gen random key and store it in redis"""
        ...

    async def get(self, key: str) -> str:
        ...
