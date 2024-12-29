from collections import defaultdict

from ..lib.lobby.lobby_manager import LobbyBackgroundManager
from ..types.setting import Setting


class LobbyCountdownService:

    def __init__(
        self,
        setting: Setting,
        background_bucket: defaultdict[str, LobbyBackgroundManager],
    ) -> None:
        self._setting = setting
        self._background_bucket = background_bucket

    async def count_down_random(self):
        """
        countdown for random gamemode
        """
        ...

    ...
