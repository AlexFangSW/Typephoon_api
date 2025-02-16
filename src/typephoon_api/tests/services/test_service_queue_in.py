from datetime import timedelta
from aio_pika.abc import AbstractExchange
from fastapi import WebSocket
from pamqp.commands import Basic
import pytest
from unittest.mock import AsyncMock, MagicMock
from asyncio import Future

from sqlalchemy.ext.asyncio import AsyncSession

from ...lib.background_tasks.base import BGManager
from ...lib.background_tasks.lobby import LobbyBG, LobbyBGMsg, LobbyBGMsgEvent

from ...repositories.game_cache import GameCacheRepo

from ...orm.game import GameStatus

from ...types.amqp import LobbyCountdownMsg, LobbyNotifyMsg

from ...types.common import LobbyUserInfo

from ...repositories.game import GameRepo

from ...repositories.lobby_cache import LobbyCacheRepo

from ...repositories.guest_token import GuestTokenRepo

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

    bg_manager = BGManager[LobbyBGMsg, LobbyBG]()

    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)

    amqp_notify_exchange: AbstractExchange = AsyncMock()
    amqp_default_exchange: AbstractExchange = AsyncMock()

    websocket: WebSocket = AsyncMock()
    websocket.receive_bytes = MagicMock(return_value=Future())

    service = QueueInService(
        setting=setting,
        token_generator=token_generator,
        token_validator=token_validator,
        bg_manager=bg_manager,
        guest_token_repo=guest_token_repo,
        sessionmaker=sessionmaker,
        amqp_notify_exchange=amqp_notify_exchange,
        amqp_default_exchange=amqp_default_exchange,
        game_cache_repo=game_cache_repo,
        lobby_cache_repo=lobby_cache_repo,
    )

    # ---------------------
    # token invalid
    # ---------------------
    websocket.cookies = {CookieNames.ACCESS_TOKEN: "invalid_access_token"}
    websocket.close = AsyncMock()

    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)
    assert websocket.close.called
    assert websocket.close.call_args.kwargs["reason"] == WSCloseReason.INVALID_TOKEN

    # ---------------------
    # create game
    # ---------------------

    # prepare access token
    player_1 = LobbyUserInfo(id="1", name="player_1")
    player_1_access_token = token_generator.gen_access_token(
        user_id=player_1.id, username=player_1.name, user_type=UserType.REGISTERED
    )

    # mocks
    websocket.cookies = {CookieNames.ACCESS_TOKEN: player_1_access_token}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())
    amqp_default_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called

    p1_notify_msg = LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    )
    assert p1_notify_msg.notify_type == LobbyBGMsgEvent.USER_JOINED

    game_id = p1_notify_msg.game_id

    # check countdown exchange
    assert amqp_default_exchange.publish.call_count == 2
    assert (
        amqp_default_exchange.publish.call_args_list[0].kwargs["routing_key"]
        == setting.amqp.lobby_multi_countdown_wait_queue
    )
    assert (
        amqp_default_exchange.publish.call_args_list[1].kwargs["routing_key"]
        == setting.amqp.game_cleanup_wait_queue
    )

    p1_countdown_msg = LobbyCountdownMsg.model_validate_json(
        amqp_default_exchange.publish.call_args.kwargs["message"].body
    )
    assert p1_countdown_msg.game_id == game_id

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 1
    ret = await lobby_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]

    # check start ts cache
    start_ts = await lobby_cache_repo.get_start_time(game_id)
    assert start_ts
    assert start_ts == datetime.now(UTC) + timedelta(
        seconds=setting.game.lobby_countdown
    )

    # check background pool
    game_connections = bg_manager._pool.get(game_id)
    assert game_connections
    assert len(game_connections) == 1

    # ---------------------
    # find game (found)
    # ---------------------
    player_2 = LobbyUserInfo(id="2", name="player_2")
    player_2_access_token = token_generator.gen_access_token(
        user_id=player_2.id, username=player_2.name, user_type=UserType.REGISTERED
    )
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
    ret = await lobby_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]
    assert player_2 == ret[player_2.id]

    # check background pool
    game_connections = bg_manager._pool.get(game_id)
    assert game_connections
    assert len(game_connections) == 2

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.USER_JOINED, game_id=game_id)

    # ---------------------
    # find game (found, reconnect)
    # ---------------------
    # player_1 reconnect
    websocket.cookies = {CookieNames.ACCESS_TOKEN: player_1_access_token}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    await service.queue_in(
        websocket=websocket, queue_in_type=QueueInType.RECONNECT, prev_game_id=game_id
    )

    # check game player count
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)

    assert game
    assert game.player_count == 2
    ret = await lobby_cache_repo.get_players(game_id)
    assert ret
    assert player_1 == ret[player_1.id]
    assert player_2 == ret[player_2.id]

    # check background pool
    game_connections = bg_manager._pool.get(game_id)
    assert game_connections
    assert len(game_connections) == 2

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.USER_JOINED, game_id=game_id)

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
    ret = await lobby_cache_repo.get_players(game_id)
    assert ret
    assert len(ret.keys()) == 3

    # check background pool
    game_connections = bg_manager._pool.get(game_id)
    assert game_connections
    assert len(game_connections) == 3

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    assert LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    ) == LobbyNotifyMsg(notify_type=LobbyBGMsgEvent.USER_JOINED, game_id=game_id)

    # clean up
    await bg_manager.cleanup()


@pytest.mark.asyncio
async def test_service_queue_in_game_full(
    setting: Setting,
    redis_conn: Redis,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    token_generator = TokenGenerator(setting)
    token_validator = TokenValidator(setting)

    bg_manager = BGManager[LobbyBGMsg, LobbyBG]()

    guest_token_repo = GuestTokenRepo(redis_conn=redis_conn, setting=setting)
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)

    amqp_notify_exchange: AbstractExchange = AsyncMock()
    amqp_default_exchange: AbstractExchange = AsyncMock()

    websocket: WebSocket = AsyncMock()
    websocket.receive_bytes = MagicMock(return_value=Future())

    service = QueueInService(
        setting=setting,
        token_generator=token_generator,
        token_validator=token_validator,
        bg_manager=bg_manager,
        guest_token_repo=guest_token_repo,
        sessionmaker=sessionmaker,
        amqp_notify_exchange=amqp_notify_exchange,
        amqp_default_exchange=amqp_default_exchange,
        game_cache_repo=game_cache_repo,
        lobby_cache_repo=lobby_cache_repo,
    )

    websocket.cookies = {}
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())
    amqp_default_exchange.publish = AsyncMock(return_value=Basic.Ack())

    # run
    for _ in range(setting.game.player_limit):
        await service.queue_in(websocket=websocket, queue_in_type=QueueInType.NEW)

    # check _amqp_notify_exchange
    assert amqp_notify_exchange.publish.called
    notify_msg = LobbyNotifyMsg.model_validate_json(
        amqp_notify_exchange.publish.call_args.kwargs["message"].body
    )
    assert notify_msg.notify_type == LobbyBGMsgEvent.GAME_START

    game_id = notify_msg.game_id

    game_connections = bg_manager._pool.get(game_id)
    assert game_connections
    assert len(game_connections) == setting.game.player_limit

    async with sessionmaker() as session:
        repo = GameRepo(session)
        game = await repo.get(game_id)
        assert game
        assert game.player_count == setting.game.player_limit
        assert game.status == GameStatus.IN_GAME

    # check game cache
    game_players = await game_cache_repo.get_players(game_id)
    assert game_players
    assert len(game_players.keys()) == setting.game.player_limit
    game_start_time = await game_cache_repo.get_start_time(game_id)
    assert game_start_time

    # clean up
    await bg_manager.cleanup()
