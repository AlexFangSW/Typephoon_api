from dataclasses import dataclass, field
from logging import getLogger

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

    def __init__(
        self,
        setting: Setting,
        game_cache_repo: GameCacheRepo,
    ) -> None:
        self._setting = setting
        self._game_cache_repo = game_cache_repo

    async def get_players(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet[GetPlayersRet]:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)
        result = GetPlayersRet()
        players = await self._game_cache_repo.get_players(game_id)

        if not players:
            logger.debug("")
            return ServiceRet(ok=True, data=result)

        for id, info in players.items():
            if id == user_id:
                result.me = info
            else:
                result.others.append(info)

        return ServiceRet(ok=True, data=result)
