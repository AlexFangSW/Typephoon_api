from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging import getLogger

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractExchange
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..types.errors import PublishNotAcknowledged

from ..types.amqp import LobbyNotifyMsg, LobbyNotifyType

from ..lib.lobby.lobby_manager import LobbyBackgroundManager

from ..types.enums import ErrorCode

from ..repositories.game import GameRepo

from ..types.common import ErrorContext, LobbyUserInfo

from .base import ServiceRet
from ..repositories.lobby_cache import LobbyCacheRepo
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
        lobby_cache_repo: LobbyCacheRepo,
        sessionmaker: async_sessionmaker[AsyncSession],
        background_bucket: defaultdict[str, LobbyBackgroundManager],
        amqp_notify_exchange: AbstractExchange,
    ) -> None:
        self._setting = setting
        self._lobby_cache_repo = lobby_cache_repo
        self._sessionmaker = sessionmaker
        self._background_bucket = background_bucket
        self._amqp_notify_exchange = amqp_notify_exchange

    async def get_countdown(
        self,
        game_id: int,
    ) -> ServiceRet[float]:
        logger.debug("game_id: %s, game_type: %s", game_id)

        start_time = await self._lobby_cache_repo.get_start_time(game_id)
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

        await self._lobby_cache_repo.remove_player(game_id=game_id,
                                                   user_id=user_id)

        # notify all servers
        msg = LobbyNotifyMsg(notify_type=LobbyNotifyType.USER_LEFT,
                             game_id=game_id,
                             user_id=user_id).model_dump_json().encode()
        amqp_msg = Message(msg, delivery_mode=DeliveryMode.PERSISTENT)
        confirm = await self._amqp_notify_exchange.publish(message=amqp_msg,
                                                           routing_key="")
        if not isinstance(confirm, Basic.Ack):
            raise PublishNotAcknowledged("publish user join message failed")

        return ServiceRet(ok=True)

    async def get_players(
        self,
        user_id: str,
        game_id: int,
    ) -> ServiceRet[GetPlayersRet]:
        logger.debug("game_id: %s, user_id: %s", game_id, user_id)

        result = GetPlayersRet()
        players = await self._lobby_cache_repo.get_players(game_id)

        if not players:
            logger.warning("game not found, game_id: %s", game_id)
            return ServiceRet(ok=False,
                              error=ErrorContext(code=ErrorCode.GAME_NOT_FOUND))

        for id, info in players.items():
            if id == user_id:
                result.me = info
            else:
                result.others.append(info)

        return ServiceRet(ok=True, data=result)
