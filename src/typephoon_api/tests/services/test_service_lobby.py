from unittest.mock import AsyncMock

from aio_pika.abc import AbstractExchange
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession

from ...types.amqp import LobbyNotifyMsg, LobbyNotifyType

from ...orm.game import GameStatus, GameType

from ...repositories.game import GameRepo

from ...types.common import LobbyUserInfo

from ...repositories.lobby_cache import LobbyCacheRepo
from ...services.lobby import LobbyService
from ..helper import *


@pytest.mark.asyncio
async def test_lobby_service_leave(
    setting: Setting, redis_conn: Redis, sessionmaker: async_sessionmaker[AsyncSession]
):

    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    amqp_notify_exchange: AbstractExchange = AsyncMock()
    amqp_notify_exchange.publish = AsyncMock(return_value=Basic.Ack())

    service = LobbyService(
        setting=setting,
        lobby_cache_repo=lobby_cache_repo,
        amqp_notify_exchange=amqp_notify_exchange,
        sessionmaker=sessionmaker,
    )

    # set up data (one game, one player)
    user_id = "123"
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.create(game_type=GameType.MULTI, status=GameStatus.LOBBY)
        game_id = game.id
        await game_repo.increase_player_count(game_id)
        await session.commit()

    await lobby_cache_repo.add_player(
        game_id=game_id, user_info=LobbyUserInfo(id=user_id, name="name")
    )

    # check
    players = await lobby_cache_repo.get_players(game_id)
    assert players
    assert len(players.keys()) == 1
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)
        assert game
        assert game.player_count == 1

    # call service
    await service.leave(user_id=user_id, game_id=game_id)

    # check
    players = await lobby_cache_repo.get_players(game_id)
    assert players == {}
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.get(game_id)
        assert game
        assert game.player_count == 0
    assert amqp_notify_exchange.publish.called
    notify_msg = (
        LobbyNotifyMsg(
            notify_type=LobbyNotifyType.USER_LEFT, game_id=game_id, user_id=user_id
        )
        .model_dump_json()
        .encode()
    )
    assert amqp_notify_exchange.publish.call_args.kwargs["message"].body == notify_msg
