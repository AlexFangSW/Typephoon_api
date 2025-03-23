from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger

from aio_pika.abc import AbstractExchange
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..repositories.lobby_cache import LobbyCacheRepo
from ..types.common import ErrorContext, LobbyUserInfo
from ..types.enums import ErrorCode
from ..types.setting import Setting
from .base import ServiceRet

logger = getLogger(__name__)


@dataclass(slots=True)
class GetPlayersRet:
    me: LobbyUserInfo
    others: list[LobbyUserInfo] = field(default_factory=list)


class LobbyService:
    def __init__(
        self,
        setting: Setting,
        lobby_cache_repo: LobbyCacheRepo,
        sessionmaker: async_sessionmaker[AsyncSession],
        amqp_notify_exchange: AbstractExchange,
    ) -> None:
        self._setting = setting
        self._lobby_cache_repo = lobby_cache_repo
        self._sessionmaker = sessionmaker
        self._amqp_notify_exchange = amqp_notify_exchange

    async def get_countdown(
        self,
        game_id: int,
    ) -> ServiceRet[float]:
        logger.debug("game_id: %s", game_id)

        start_time = await self._lobby_cache_repo.get_start_time(game_id)
        if not start_time:
            logger.warning("start time not found, game_id: %s", game_id)
            return ServiceRet(
                ok=False, error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND)
            )

        seconds_left = (start_time - datetime.now(UTC)).total_seconds()
        return ServiceRet(ok=True, data=seconds_left if seconds_left >= 0 else 0)

    async def get_players(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet[GetPlayersRet]:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        players = await self._lobby_cache_repo.get_players(game_id)

        if not players:
            logger.warning("game not found, game_id: %s", game_id)
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

        others = [info for _, info in players.items()]

        return ServiceRet(ok=True, data=GetPlayersRet(me=me, others=others))
