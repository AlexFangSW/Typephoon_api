from datetime import timedelta
from httpx import AsyncClient
import pytest

from ...types.responses.lobby import LobbyCountdownResponse

from ...types.enums import CookieNames

from ...types.common import LobbyUserInfo

from ...repositories.lobby_cache import LobbyCacheRepo

from ...lib.token_generator import TokenGenerator

from ..helper import *


@pytest.mark.asyncio
async def test_api_lobby_players(
    client: AsyncClient,
    redis_conn: Redis,
    setting: Setting,
):
    game_id = 123

    # insert players to cache
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for i in range(setting.game.player_limit):
        await lobby_cache_repo.add_player(game_id=game_id,
                                          user_info=LobbyUserInfo(
                                              id=f"player-{i}",
                                              name=f"player-name-{i}"))

    # get player
    token_generator = TokenGenerator(setting)
    access_token = token_generator.gen_access_token(user_id="player-1",
                                                    username="player-name-1")
    ret = await client.get(f"{API_PREFIX}/lobby/players",
                           params={"game_id": game_id},
                           cookies={CookieNames.ACCESS_TOKEN: access_token})
    result = ret.json()
    assert result == {
        'ok':
            True,
        'me': {
            'id': 'player-1',
            'name': 'player-name-1',
        },
        'others': [{
            'id': 'player-0',
            'name': 'player-name-0',
        }, {
            'id': 'player-2',
            'name': 'player-name-2',
        }, {
            'id': 'player-3',
            'name': 'player-name-3',
        }, {
            'id': 'player-4',
            'name': 'player-name-4',
        }]
    }


@pytest.mark.asyncio
async def test_api_lobby_countdown(
    client: AsyncClient,
    redis_conn: Redis,
    setting: Setting,
):
    game_id = 123

    # set start time
    start_time = datetime.now(UTC) + timedelta(
        seconds=setting.game.lobby_countdown)

    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_cache_repo.set_start_time(game_id=game_id,
                                          start_time=start_time)

    # call api
    ret = await client.get(f"{API_PREFIX}/lobby/countdown",
                           params={"game_id": game_id})
    result = LobbyCountdownResponse.model_validate(ret.json())
    assert result.ok
    assert result.seconds_left > 0
