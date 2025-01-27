from dataclasses import dataclass, field
from logging import getLogger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from ..types.enums import UserType
from ..repositories.game_result import (
    GameResultRepo,
    GameResultWithGameType,
    StatisticsRet,
)
from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class HistoryRet:
    total: int = 0
    has_prev_page: bool = False
    has_next_page: bool = False
    data: list[GameResultWithGameType] = field(default_factory=list)


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
            statistics = await repo.statistics(user_id)
            return ServiceRet(ok=True, data=statistics)

    async def graph(
        self, user_id: str, user_type: UserType, size: int
    ) -> ServiceRet[list[GameResultWithGameType]]:
        if user_type == UserType.GUEST:
            logger.debug("ignore guest user")
            return ServiceRet(ok=True, data=[])

        async with self._sessionmaker() as session:
            repo = GameResultRepo(session)
            statistics = await repo.last_n_games_with_game_type(
                user_id=user_id, size=size
            )
            return ServiceRet(ok=True, data=statistics)

    async def history(
        self, user_id: str, user_type: UserType, size: int, page: int
    ) -> ServiceRet[HistoryRet]:
        if user_type == UserType.GUEST:
            logger.debug("ignore guest user")
            return ServiceRet(ok=True, data=HistoryRet())

        async with self._sessionmaker() as session:
            repo = GameResultRepo(session)
            results = await repo.last_n_games_with_game_type(
                user_id=user_id, size=size, page=page
            )
            total = await repo.total_games(user_id)

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
