from datetime import timedelta
import pytest
from redis.asyncio import Redis

from ...repositories.game_cache import GameCacheRepo

from ...types.common import GameUserInfo, LobbyUserInfo

from ...repositories.lobby_cache import LobbyCacheRepo

from ..helper import *


@pytest.mark.asyncio
async def test_game_cache_repo_populate_with_lobby_cache(
    redis_conn: Redis, setting: Setting
):

    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    lobby_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        await lobby_repo.add_player(game_id=dummy_game_id, user_info=player)

    # set start time
    await lobby_repo.set_start_time(game_id=dummy_game_id, start_time=NOW)

    game_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_repo.populate_with_lobby_cache(
        game_id=dummy_game_id, lobby_cache_repo=lobby_repo
    )

    # check
    game_players = await game_repo.get_players(dummy_game_id)
    assert game_players
    for player in players:
        assert game_players[player.id] == GameUserInfo(id=player.id, name=player.name)

    game_start_time = await game_repo.get_start_time(dummy_game_id)
    assert game_start_time == NOW + timedelta(seconds=setting.game.start_countdown)


@pytest.mark.asyncio
async def test_game_cache_repo_populate_with_lobby_cache_auto_clean(
    redis_conn: Redis, setting: Setting
):

    dummy_game_id = 123123
    players = [
        LobbyUserInfo(id=f"{i}", name=f"player-{i}")
        for i in range(setting.game.player_limit)
    ]

    # add players
    lobby_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for player in players:
        await lobby_repo.add_player(game_id=dummy_game_id, user_info=player)

    # set start time
    await lobby_repo.set_start_time(game_id=dummy_game_id, start_time=NOW)

    game_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_repo.populate_with_lobby_cache(
        game_id=dummy_game_id, lobby_cache_repo=lobby_repo, auto_clean=True
    )

    # check
    game_players = await game_repo.get_players(dummy_game_id)
    assert game_players
    for player in players:
        assert game_players[player.id] == GameUserInfo(id=player.id, name=player.name)

    game_start_time = await game_repo.get_start_time(dummy_game_id)
    assert game_start_time == NOW + timedelta(seconds=setting.game.start_countdown)

    assert not await lobby_repo.get_players(dummy_game_id)
    assert not await lobby_repo.get_start_time(dummy_game_id)
