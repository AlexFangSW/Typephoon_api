from collections import defaultdict
from aio_pika.abc import AbstractExchange
from fastapi import WebSocket
import pytest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.game_cache import GameCacheRepo

from ...repositories.guest_token import GuestTokenRepo

from ...lib.lobby.lobby_manager import LobbyBackgroundManager

from ...lib.token_validator import TokenValidator

from ...lib.token_generator import TokenGenerator
from ...services.queue_in import QueueInService
from ...types.enums import CookieNames, QueueInType, WSCloseReason
from ..helper import *


@pytest.mark.asyncio
async def test_service_queue_in(
    setting: Setting,
    redis_conn: Redis,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)
    backgrond_bucket: defaultdict[str, LobbyBackgroundManager] = defaultdict(
        LobbyBackgroundManager)
    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)

    amqp_notify_exchange: AbstractExchange = AsyncMock()
    amqp_countdown_exchange: AbstractExchange = AsyncMock()

    websocket: WebSocket = AsyncMock()

    service = QueueInService(
        setting=setting,
        token_generator=token_generator,
        token_validator=token_validator,
        background_bucket=backgrond_bucket,
        guest_token_repo=guest_token_repo,
        sessionmaker=sessionmaker,
        amqp_notify_exchange=amqp_notify_exchange,
        amqp_countdown_exchange=amqp_countdown_exchange,
        game_cache_repo=game_cache_repo,
    )

    # ---------------------
    # token invalid
    # ---------------------
    websocket.cookies = {CookieNames.ACCESS_TOKEN: "invalid_access_token"}
    websocket.close = AsyncMock()

    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)
    assert websocket.close.called
    assert websocket.close.call_args.kwargs[
        'reason'] == WSCloseReason.INVALID_TOKEN

    # ---------------------
    # find game (found)
    # ---------------------

    # create game
    # run
    # check game player count
    # check _amqp_notify_exchange

    # ---------------------
    # find game (found, reconnect)
    # ---------------------

    # create game, add player to game
    # run
    # check game player count need to be same
    # check _amqp_notify_exchange

    # ---------------------
    # create game
    # ---------------------

    # run
    # check game player count
    # check _amqp_notify_exchange

    # ---------------------
    # guest user
    # ---------------------
    # check websocket, notfiy user to get token
