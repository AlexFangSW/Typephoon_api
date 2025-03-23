from collections.abc import Callable, Coroutine
from typing import Any


class AsyncDefaultdict[K, V]:
    def __init__(
        self,
        init_callback: Callable[[], Coroutine[Any, Any, V]],
    ) -> None:
        self._dict: dict[K, V] = {}
        self._init_callback = init_callback

    async def get(self, key: K) -> V:
        """
        Acts like defaultdict, return if exist, create if not found
        """
        if self._dict.get(key):
            return self._dict[key]
        else:
            value = await self._init_callback()
            self._dict[key] = value
            return value

    async def pop(self, key: K):
        self._dict.pop(key)

    def items(self):
        return self._dict.items()
