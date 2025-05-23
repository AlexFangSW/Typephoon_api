from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game import GameRepo
from ..repositories.game_cache import GameCacheRepo
from ..repositories.game_result import GameResultRepo
from ..types.common import ErrorContext, GameUserInfo
from ..types.enums import ErrorCode, UserType
from ..types.requests.game import GameStatistics
from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class GetResultRet:
    """
    players are sorted by their ranking
    """

    ranking: list[GameUserInfo] = field(default_factory=list)

    def __post_init__(self):
        self.ranking = sorted(self.ranking, key=lambda x: x.rank)


@dataclass(slots=True)
class GetPlayersRet:
    me: GameUserInfo
    others: dict[str, GameUserInfo] = field(default_factory=dict)


class GameService:
    def __init__(
        self,
        game_cache_repo: GameCacheRepo,
        sessionmaker: async_sessionmaker[AsyncSession],
    ):
        self._game_cache_repo = game_cache_repo
        self._sessionmaker = sessionmaker

    async def get_countdown(self, game_id: int) -> ServiceRet[float]:
        logger.debug("game_id: %s", game_id)

        start_time = await self._game_cache_repo.get_start_time(game_id)
        if not start_time:
            logger.warning("start time not found, game_id: %s", game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
            )

        seconds_left = (start_time - datetime.now(UTC)).total_seconds()
        return ServiceRet(ok=True, data=seconds_left if seconds_left >= 0 else 0)

    async def write_statistics(
        self,
        statistics: GameStatistics,
        user_id: str,
        username: str,
        user_type: UserType,
    ) -> ServiceRet:
        logger.debug(
            "statistics: %s, user_id: %s, username: %s, user_type: %s",
            statistics.model_dump_json(),
            user_id,
            username,
            str(user_type),
        )

        players = await self._game_cache_repo.get_players(statistics.game_id)
        if players is None:
            logger.warning("game not found, game_id: %s", statistics.game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
            )

        if user_id not in players:
            logger.warning(
                "not a participant, game_id: %s, user_id: %s",
                statistics.game_id,
                user_id,
            )
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.NOT_A_PARTICIPANT)
            )

        # write to database
        async with self._sessionmaker() as session:
            # get ranking
            game_repo = GameRepo(session)
            game = await game_repo.increase_finish_count(id=statistics.game_id)
            if not game:
                logger.warning("game not found, game_id: %s", game)
                return ServiceRet(
                    ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
                )

            finished_at = datetime.now(UTC)
            rank = game.finish_count

            # record result for registered user
            if user_type == UserType.REGISTERED:
                result_repo = GameResultRepo(session)
                await result_repo.create(
                    game_id=statistics.game_id,
                    user_id=user_id,
                    rank=rank,
                    wpm_raw=statistics.wpm_raw,
                    wpm_correct=statistics.wpm,
                    accuracy=statistics.acc,
                    finished_at=finished_at,
                )

            await session.commit()

        # update cache
        async with self._game_cache_repo.lock(game_id=statistics.game_id):
            await self._game_cache_repo.update_player_cache(
                game_id=statistics.game_id,
                data=GameUserInfo(
                    id=user_id,
                    name=username,
                    finished=finished_at.isoformat(),
                    rank=rank,
                    wpm=statistics.wpm,
                    wpm_raw=statistics.wpm_raw,
                    acc=statistics.acc,
                ),
            )

        return ServiceRet(ok=True)

    async def get_players(
        self, game_id: int, user_id: str
    ) -> ServiceRet[GetPlayersRet]:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        players = await self._game_cache_repo.get_players(game_id)
        if not players:
            logger.warning("players not found, game_id: %s", game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
            )

        me = players.pop(user_id, None)
        if me is None:
            logger.warning(
                "not a participant, game_id: %s, user_id: %s", game_id, user_id
            )
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.NOT_A_PARTICIPANT)
            )

        return ServiceRet(ok=True, data=GetPlayersRet(me=me, others=players))

    async def get_result(self, game_id: int) -> ServiceRet[GetResultRet]:
        logger.debug("game_id: %s", game_id)

        players = await self._game_cache_repo.get_players(game_id)
        if not players:
            logger.warning("players not found, game_id: %s", game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
            )

        temp_list: list[GameUserInfo] = []
        for _, player_info in players.items():
            temp_list.append(player_info)

        return ServiceRet(ok=True, data=GetResultRet(ranking=temp_list))

    async def get_words(self, game_id: int) -> ServiceRet[str]:
        """
        Get words from cache
        """
        logger.debug("game_id: %s", game_id)

        # retrive words, words should be already generated at lobby stage
        words = await self._game_cache_repo.get_words(game_id)
        if words is None:
            logger.warning("word not found, game_id: %s", game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.WORDS_NOT_FOUND)
            )

        return ServiceRet(ok=True, data=words)
