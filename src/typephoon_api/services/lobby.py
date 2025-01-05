from dataclasses import dataclass, field
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.game import GameRepo

from ..types.common import LobbyUserInfo

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

    async def leave(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        async with self._sessionmaker() as session:
            repo = GameRepo(session)
            await repo.decrease_player_count(game_id)
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
            return ServiceRet(ok=True, data=result)

        for id, info in players.items():
            if id == user_id:
                result.me = info
            else:
                result.others.append(info)

        return ServiceRet(ok=True, data=result)
