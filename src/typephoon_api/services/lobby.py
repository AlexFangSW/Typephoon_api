from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Context
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..types.enums import ErrorCode

from ..orm.game import GameType

from ..repositories.game import GameRepo

from ..types.common import ErrorContext, LobbyUserInfo

from .base import ServiceRet
from ..repositories.game_cache import GameCacheRepo
from ..types.setting import Setting

logger = getLogger(__name__)


@dataclass(slots=True)
class GetPlayersRet:
    me: LobbyUserInfo | None = None
    others: list[LobbyUserInfo] = field(default_factory=list)


class LobbyService:

    def __init__(self, setting: Setting, game_cache_repo: GameCacheRepo,
                 sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._setting = setting
        self._game_cache_repo = game_cache_repo
        self._sessionmaker = sessionmaker

    async def get_countdown(
        self,
        game_id: int,
        game_type: GameType,
    ) -> ServiceRet[float]:
        logger.debug("game_id: %s, game_type: %s", game_id, game_type)

        start_time = await self._game_cache_repo.get_start_time(game_id)
        if not start_time:
            logger.warning("start time not found, game_id: %s", game_id)
            return ServiceRet(ok=False,
                              error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

        seconds_left = (start_time - datetime.now(UTC)).total_seconds()
        return ServiceRet(ok=True, data=seconds_left)

    async def leave(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        async with self._sessionmaker() as session:
            repo = GameRepo(session)
            game = await repo.decrease_player_count(game_id)

            if not game:
                logger.warning("game not found, game_id: %s", game_id)
                return ServiceRet(
                    ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

            await session.commit()

        await self._game_cache_repo.remove_player(game_id=game_id,
                                                  user_id=user_id)
        return ServiceRet(ok=True)

    async def get_players(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet[GetPlayersRet]:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        result = GetPlayersRet()
        players = await self._game_cache_repo.get_players(game_id)

        if not players:
            logger.warning("game found, game_id: %s", game_id)
            return ServiceRet(ok=False,
                              error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

        for id, info in players.items():
            if id == user_id:
                result.me = info
            else:
                result.others.append(info)

        return ServiceRet(ok=True, data=result)
