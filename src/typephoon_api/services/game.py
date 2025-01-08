from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger
from os import stat
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game import GameRepo

from ..repositories.game_result import GameResultRepo

from ..types.common import ErrorContext, GameUserInfo
from ..types.enums import ErrorCode

from ..repositories.game_cache import GameCacheRepo
from ..types.requests.game import GameStatistics
from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class GetResultRetItem:
    id: str
    name: str

    finished: str | None = None
    rank: int = -1
    wpm: float | None = None
    wpm_raw: float | None = None
    acc: float | None = None

    @classmethod
    def from_game_cache(cls, inpt: GameUserInfo) -> Self:
        return cls(
            id=inpt.id,
            name=inpt.name,
            finished=inpt.finished,
            rank=inpt.rank,
            wpm=inpt.wpm,
            wpm_raw=inpt.wpm_raw,
            acc=inpt.acc,
        )


@dataclass(slots=True)
class GetResultRet:
    """
    players are sorted by their ranking
    """
    ranking: list[GetResultRetItem] = field(default_factory=list)

    def __post_init__(self):
        self.ranking = sorted(self.ranking, key=lambda x: x.rank)


class GameService:

    def __init__(self, game_cache_repo: GameCacheRepo,
                 sessionmaker: async_sessionmaker[AsyncSession]):
        self._game_cache_repo = game_cache_repo
        self._sessionmaker = sessionmaker

    async def get_countdown(self, game_id: int) -> ServiceRet[float]:
        start_time = await self._game_cache_repo.get_start_time(game_id)
        if not start_time:
            logger.warning("start time not found, game_id: %s", game_id)
            return ServiceRet(ok=False,
                              error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

        seconds_left = (start_time - datetime.now(UTC)).total_seconds()
        return ServiceRet(ok=True, data=seconds_left)

    # TODO: xxxx
    async def write_statistics(self, statistics: GameStatistics,
                               user_id: str) -> ServiceRet:
        # write to database
        async with self._sessionmaker() as session:
            game_repo = GameRepo(session)
            game = await game_repo.get(id=statistics.game_id, lock=True)
            if not game:
                logger.warning("game not found, game_id: %s", game)
                return ServiceRet(
                    ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

            result_repo = GameResultRepo(session)
            game_result = await result_repo.create(
                game_id=statistics.game_id,
                user_id=user_id,
                rank=999,
                wpm_raw=statistics.wpm_raw,
                wpm_currect=statistics.wpm,
                accuracy=statistics.acc,
                finished_at=datetime.now(UTC),
            )

            await session.commit()

        # write to cache

        return ServiceRet(ok=True)

    async def get_result(self, game_id: int) -> ServiceRet[GetResultRet]:
        players = await self._game_cache_repo.get_players(game_id)
        if not players:
            logger.warning("start time not found, game_id: %s", game_id)
            return ServiceRet(ok=False,
                              error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

        temp_list: list[GetResultRetItem] = []
        for _, player_info in players.items():
            temp_list.append(GetResultRetItem.from_game_cache(player_info))

        return ServiceRet(ok=True, data=GetResultRet(ranking=temp_list))
