from datetime import datetime
from ..types.common import LobbyUserInfo


class GameCacheRepo:

    def __init__(self) -> None:
        pass

    async def add_player(self, game_id: int, user_info: LobbyUserInfo):
        ...

    async def set_start_time(self, game_id: int, start_time: datetime):
        ...

    ...
