from dataclasses import dataclass, field
from datetime import datetime

from ..types.common import GameTypeStr

from .base import ServiceRet


@dataclass(slots=True)
class StatisticsRet:
    """
    Attrubutes:
    - Best WPM
    - Average WPM of last 10 games
    - Average WPM of all games
    """

    best: float = 0
    last_10: float = 0
    average: float = 0


@dataclass(slots=True)
class GameResultItem:
    game_type: GameTypeStr
    game_id: int
    wpm: float
    wpm_raw: float
    accuracy: float
    finished_at: datetime
    rank: int


@dataclass(slots=True)
class HistoryRet:
    total: int
    has_prev_page: bool
    has_next_page: bool
    data: list[GameResultItem] = field(default_factory=list)


# TODO
class ProfileService:

    def __init__(self) -> None:
        pass

    async def statistics(self, user_id: str) -> ServiceRet[StatisticsRet]: ...

    async def graph(
        self, user_id: str, size: int
    ) -> ServiceRet[list[GameResultItem]]: ...

    async def history(
        self, user_id: str, size: int, page: int
    ) -> ServiceRet[HistoryRet]: ...
