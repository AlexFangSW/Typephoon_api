from logging import getLogger

from .base import LobbyBGNotifyMsg

from .lobby_background import LobbyBackground

logger = getLogger(__name__)


class LobbyBackgroundManager:

    def __init__(self) -> None:
        self._background_tasks: dict[str, LobbyBackground] = {}

    async def add(self, bg: LobbyBackground):
        self._background_tasks[bg.user_info.id] = bg

    async def remove(self, user_id: str):
        self._background_tasks.pop(user_id)

    async def broadcast(self, msg: LobbyBGNotifyMsg):
        for _, bg in self._background_tasks.items():
            await bg.notifiy(msg)

    async def stop(self, final_msg: LobbyBGNotifyMsg | None = None):
        for _, bg in self._background_tasks.items():
            await bg.stop(final_msg)
