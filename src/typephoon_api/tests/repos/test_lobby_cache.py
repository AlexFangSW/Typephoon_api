import json

import pytest
from redis.asyncio import Redis

from ...repositories.lobby_cache import LobbyCacheRepo, LobbyCacheType
from ...types.common import LobbyUserInfo
from ..helper import *


@pytest.mark.asyncio
async def test_lobby_cache_repo_add_players(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        ret = await repo.add_player(game_id=dummy_game_id, user_info=player)
        assert ret

    ret = await repo.add_player(game_id=dummy_game_id, user_info=players[0])
    assert not ret

    # check
    key = repo._gen_cache_key(game_id=dummy_game_id, cache_type=LobbyCacheType.PLAYERS)
    ret = await redis_conn.get(key)
    assert ret
    data: dict = json.loads(ret)
    assert len(data.keys()) == len(players)
    for player in players:
        assert player == LobbyUserInfo.model_validate(data[player.id])


@pytest.mark.asyncio
async def test_lobby_cache_repo_get_players(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        await repo.add_player(game_id=dummy_game_id, user_info=player)

    # check
    result = await repo.get_players(dummy_game_id)
    assert result
    for player in players:
        assert player == result[player.id]


@pytest.mark.asyncio
async def test_lobby_cache_repo_remove_players(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        await repo.add_player(game_id=dummy_game_id, user_info=player)

    result = await repo.get_players(dummy_game_id)
    assert result
    assert len(result.keys()) == len(players)

    # remove player
    await repo.remove_player(game_id=dummy_game_id, user_id=players[0].id)

    result = await repo.get_players(dummy_game_id)
    assert result
    assert len(result.keys()) == len(players) - 1
    assert players[0].id not in result


@pytest.mark.asyncio
async def test_lobby_cache_repo_is_new_player(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        await repo.add_player(game_id=dummy_game_id, user_info=player)

    result = await repo.get_players(dummy_game_id)
    assert result
    assert len(result.keys()) == len(players)

    assert await repo.is_new_player(game_id=dummy_game_id, user_id="does not exist")
    assert not await repo.is_new_player(game_id=dummy_game_id, user_id=players[0].id)


@pytest.mark.asyncio
async def test_lobby_cache_repo_set_start_time(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await repo.set_start_time(game_id=dummy_game_id, start_time=NOW)

    key = repo._gen_cache_key(
        game_id=dummy_game_id, cache_type=LobbyCacheType.COUNTDOWN
    )
    ret: bytes = await redis_conn.get(key)
    assert ret
    assert datetime.fromisoformat(ret.decode()) == NOW


@pytest.mark.asyncio
async def test_lobby_cache_repo_get_start_time(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123
    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await repo.set_start_time(game_id=dummy_game_id, start_time=NOW)

    ret = await repo.get_start_time(game_id=dummy_game_id)
    assert ret
    assert ret == NOW


@pytest.mark.asyncio
async def test_lobby_cache_repo_clear_cache(redis_conn: Redis, setting: Setting):
    dummy_game_id = 123123

    repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    # set cache
    await repo.set_start_time(game_id=dummy_game_id, start_time=NOW)
    await repo.add_player(
        game_id=dummy_game_id, user_info=LobbyUserInfo(id="1", name="player-1")
    )
    # clear
    await repo.clear_cache(dummy_game_id)

    ret = await repo.get_start_time(dummy_game_id)
    assert ret is None
    ret = await repo.get_players(dummy_game_id)
    assert ret is None
