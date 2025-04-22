from dataclasses import dataclass, field
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game_result import (
    GameResultRepo,
    GameResultWithGameType,
)
from ..types.enums import UserType
from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class HistoryRet:
    total: int = 0
    has_prev_page: bool = False
    has_next_page: bool = False
    data: list[GameResultWithGameType] = field(default_factory=list)


@dataclass(slots=True)
class StatisticsRet:
    total: int = 0

    wpm_best: float = 0
    wpm_avg_10: float = 0
    wpm_avg_all: float = 0

    acc_best: float = 0
    acc_avg_10: float = 0
    acc_avg_all: float = 0


class ProfileService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker
        pass

    async def statistics(
        self, user_id: str, user_type: UserType
    ) -> ServiceRet[StatisticsRet]:
        if user_type == UserType.GUEST:
            logger.debug("ignore guest user")
            return ServiceRet(ok=True, data=StatisticsRet())

        async with self._sessionmaker() as session:
            repo = GameResultRepo(session)
            avg_all = await repo.get_avg_last_n_games(user_id=user_id)
            avg_last_10 = await repo.get_avg_last_n_games(user_id=user_id, last_n=10)
            best_game = await repo.get_best(user_id)
            total_games = await repo.get_total_games(user_id)

        return ServiceRet(
            ok=True,
            data=StatisticsRet(
                total=total_games,
                wpm_best=best_game.wpm_correct if best_game else 0,
                wpm_avg_10=avg_last_10.wpm,
                wpm_avg_all=avg_all.wpm,
                acc_best=best_game.accuracy if best_game else 0,
                acc_avg_10=avg_last_10.acc,
                acc_avg_all=avg_all.acc,
            ),
        )

    async def graph(
        self, user_id: str, user_type: UserType, size: int
    ) -> ServiceRet[list[GameResultWithGameType]]:
        if user_type == UserType.GUEST:
            logger.debug("ignore guest user")
            return ServiceRet(ok=True, data=[])

        async with self._sessionmaker() as session:
            repo = GameResultRepo(session)
            statistics = await repo.get_last_n_games_with_game_type(
                user_id=user_id, size=size
            )
            return ServiceRet(
                ok=True, data=sorted(statistics, key=lambda x: x.finished_at)
            )

    async def history(
        self, user_id: str, user_type: UserType, size: int, page: int
    ) -> ServiceRet[HistoryRet]:
        if user_type == UserType.GUEST:
            logger.debug("ignore guest user")
            return ServiceRet(ok=True, data=HistoryRet())

        async with self._sessionmaker() as session:
            repo = GameResultRepo(session)
            results = await repo.get_last_n_games_with_game_type(
                user_id=user_id, size=size, page=page
            )
            total = await repo.get_total_games(user_id)

        has_prev_page = True if page > 1 else False
        has_next_page = True if total > (page * size) else False

        return ServiceRet(
            ok=True,
            data=HistoryRet(
                total=total,
                has_prev_page=has_prev_page,
                has_next_page=has_next_page,
                data=results,
            ),
        )
