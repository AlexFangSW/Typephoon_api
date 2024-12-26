from typing import Any

from .lobby_background_random import LobbyBackgroundRandom


class LobbyBackgroundManager:

    def __init__(self) -> None:
        self._background_tasks: list[LobbyBackgroundRandom] = []

    async def add(self, bg: LobbyBackgroundRandom):
        self._background_tasks.append(bg)

    async def broadcast(self, msg: Any):
        for bg in self._background_tasks:
            await bg.notifiy(msg)

    async def stop(self):
        for bg in self._background_tasks:
            await bg.stop()
