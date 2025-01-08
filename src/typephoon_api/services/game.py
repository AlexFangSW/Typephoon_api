from dataclasses import dataclass, field
from ..types.requests.game import GameStatistics
from .base import ServiceRet


@dataclass(slots=True)
class GetResultRetItem:
    user_id: str
    username: str
    ranking: int
    wpm: float
    wpm_raw: float
    acc: float
    acc_raw: float


@dataclass(slots=True)
class GetResultRet:
    """
    players are sorted by their ranking
    """
    ranking: list[GetResultRetItem] = field(default_factory=list)

    def __post_init__(self):
        self.ranking = sorted(self.ranking, key=lambda x: x.ranking)


class GameService:

    def __init__(self):
        ...

    async def get_countdown(self, game_id: int) -> ServiceRet[float]:
        ...

    async def write_statistics(self, statistics: GameStatistics,
                               user_id: str) -> ServiceRet:
        ...

    async def get_result(self, game_id: int) -> ServiceRet[GetResultRet]:
        ...
