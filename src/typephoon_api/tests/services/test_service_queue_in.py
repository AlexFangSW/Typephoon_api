from collections import defaultdict
from datetime import timedelta
from aio_pika.abc import AbstractExchange
from fastapi import WebSocket
from pamqp.commands import Basic
import pytest
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from ...types.amqp import LobbyCountdownMsg, LobbyNotifyMsg, LobbyNotifyType

from ...types.common import LobbyUserInfo

from ...repositories.game import GameRepo

from ...repositories.game_cache import GameCacheRepo

from ...repositories.guest_token import GuestTokenRepo

from ...lib.lobby.lobby_manager import LobbyBackgroundManager

from ...lib.token_validator import TokenValidator

from ...lib.token_generator import TokenGenerator
from ...services.queue_in import QueueInService
from ...types.enums import CookieNames, QueueInType, UserType, WSCloseReason
from ..helper import *
import time_machine


@pytest.mark.asyncio
@time_machine.travel(NOW, tick=False)
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
    # create game
    # ---------------------

    # prepare access token
    player_1 = LobbyUserInfo(id="1", name="player_1")
    player_1_access_token = token_generator.gen_access_token(
        user_id=player_1.id,
        username=player_1.name,
        user_type=UserType.REGISTERED)

    # mocks
    websocket.cookies = {CookieNames.ACCESS_TOKEN: player_1_access_token}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())
    amqp_countdown_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert amqp_notify_exchange.publish.call_args.kwargs[
        "routing_key"] == setting.amqp.lobby_notify_queue

    p1_notify_msg = LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body)
    assert p1_notify_msg.notify_type == LobbyNotifyType.USER_JOINED

    game_id = p1_notify_msg.game_id

    # check countdown exchange
    assert amqp_countdown_exchange.publish.called
    assert amqp_countdown_exchange.publish.call_args.kwargs[
        "routing_key"] == setting.amqp.lobby_random_countdown_wait_queue

    p1_countdown_msg = LobbyCountdownMsg.model_validate_json(
        amqp_countdown_exchange.publish.call_args.kwargs["message"].body)
    assert p1_countdown_msg.game_id == game_id

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 1
    ret = await game_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]

    # check start ts cache
    start_ts = await game_cache_repo.get_start_time(game_id)
    assert start_ts
    assert start_ts == datetime.now(UTC) + timedelta(
        seconds=setting.game.lobby_countdown)

    # check background bucket
    assert len(backgrond_bucket[str(game_id)]._background_tasks) == 1

    # ---------------------
    # find game (found)
    # ---------------------
    player_2 = LobbyUserInfo(id="2", name="player_2")
    player_2_access_token = token_generator.gen_access_token(
        user_id=player_2.id,
        username=player_2.name,
        user_type=UserType.REGISTERED)
    websocket.cookies = {CookieNames.ACCESS_TOKEN: player_2_access_token}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 2
    ret = await game_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]
    assert player_2 == ret[player_2.id]

    # check background bucket
    assert len(backgrond_bucket[str(game_id)]._background_tasks) == 2

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert amqp_notify_exchange.publish.call_args.kwargs[
        "routing_key"] == setting.amqp.lobby_notify_queue
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED,
                        game_id=game_id)

    # ---------------------
    # find game (found, reconnect)
    # ---------------------
    # player_1 reconnect
    websocket.cookies = {CookieNames.ACCESS_TOKEN: player_1_access_token}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())
    await backgrond_bucket[str(game_id)].remove(player_1.id)

    # run
    await service.queue_in(websocket=websocket,
                           queue_in_type=QueueInType.RECONNECT,
                           prev_game_id=game_id)

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 2
    ret = await game_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]
    assert player_2 == ret[player_2.id]

    # check background bucket
    assert len(backgrond_bucket[str(game_id)]._background_tasks) == 2

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert amqp_notify_exchange.publish.call_args.kwargs[
        "routing_key"] == setting.amqp.lobby_notify_queue
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED,
                        game_id=game_id)

    # ---------------------
    # guest user
    # ---------------------
    websocket.cookies = {}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 3
    ret = await game_cache_repo.get_players(game_id)
    assert ret
    assert len(ret.keys()) == 3

    # check background bucket
    assert len(backgrond_bucket[str(game_id)]._background_tasks) == 3

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert amqp_notify_exchange.publish.call_args.kwargs[
        "routing_key"] == setting.amqp.lobby_notify_queue
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED,
                        game_id=game_id)
