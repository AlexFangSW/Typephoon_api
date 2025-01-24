from dataclasses import dataclass

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
class GraphRet: ...


@dataclass(slots=True)
class HistoryRet: ...


class ProfileService:
    def __init__(self) -> None:
        pass

    async def statistics(self, user_id: str) -> ServiceRet[StatisticsRet]: ...

    async def graph(self, user_id: str, size: int) -> ServiceRet[GraphRet]: ...

    async def history(
        self, user_id: str, size: int, page: int
    ) -> ServiceRet[HistoryRet]: ...
