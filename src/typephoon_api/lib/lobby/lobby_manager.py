from .base import LobbyBGNotifyMsg

from .lobby_background import LobbyBackground


class LobbyBackgroundManager:

    def __init__(self) -> None:
        self._background_tasks: list[LobbyBackground] = []

    async def add(self, bg: LobbyBackground):
        self._background_tasks.append(bg)

    async def broadcast(self, msg: LobbyBGNotifyMsg):
        for bg in self._background_tasks:
            await bg.notifiy(msg)

    async def stop(self):
        for bg in self._background_tasks:
            await bg.stop()
