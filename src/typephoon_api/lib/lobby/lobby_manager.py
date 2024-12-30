from .base import LobbyBGNotifyMsg
from ...types.amqp import LobbyNotifyType

from .lobby_background import LobbyBackground


class LobbyBackgroundManager:

    def __init__(self) -> None:
        self._background_tasks: list[LobbyBackground] = []

    async def add(self, bg: LobbyBackground):
        self._background_tasks.append(bg)
        msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED)
        await self.broadcast(msg)

    async def broadcast(self, msg: LobbyBGNotifyMsg):
        for bg in self._background_tasks:
            await bg.notifiy(msg)

    async def stop(self):
        for bg in self._background_tasks:
            await bg.stop()

    async def server_shutdown(self):
        """
        Sends reconnect event to all users
        """
        for bg in self._background_tasks:
            await bg.server_shutdown()
