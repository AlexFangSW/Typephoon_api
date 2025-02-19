from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.user import UserRepo

from ...orm.game import GameStatus, GameType
from ...repositories.game import GameRepo

from ...types.common import LobbyUserInfo

from ...repositories.lobby_cache import LobbyCacheRepo

from ...lib.token_generator import TokenGenerator

from ...types.requests.game import GameStatistics
from ...types.enums import CookieNames, ErrorCode, UserType
from ...types.responses.base import ErrorResponse, SuccessResponse
from ...types.responses.game import GameCountdownResponse, GameResultResponse
from ...repositories.game_cache import GameCacheRepo
from ..helper import *


@pytest.mark.asyncio
async def test_game_countdown(client: AsyncClient, redis_conn: Redis, setting: Setting):
    game_id = 123

    # countdown not found
    ret = await client.get(f"{API_PREFIX}/game/countdown", params={"game_id": game_id})
    assert ret.status_code == 404
    data = ErrorResponse.model_validate(ret.json())
    assert data.ok == False
    assert data.error.code == ErrorCode.GAME_NOT_FOUND

    # prepare cache
    start_time = datetime.now(UTC) + timedelta(seconds=setting.game.start_countdown)
    lobby_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_repo.set_start_time(game_id=game_id, start_time=start_time)
    game_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_repo, auto_clean=True
    )

    ret = await client.get(f"{API_PREFIX}/game/countdown", params={"game_id": game_id})
    assert ret.status_code == 200
    data = GameCountdownResponse.model_validate(ret.json())
    assert data.ok == True
    assert data.seconds_left > 0


@pytest.mark.asyncio
async def test_game_write_statistics(
    client: AsyncClient,
    setting: Setting,
    redis_conn: Redis,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    game_id = 123
    user_id = "123"
    username = "123-name"
    statistics = GameStatistics(game_id=game_id, wpm=123, wpm_raw=200, acc=60)
    access_token = TokenGenerator(setting).gen_access_token(
        user_id=user_id, username=username
    )

    # bad token
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: "qqq.bbb.ccc"},
    )
    assert ret.status_code == 400
    data = ErrorResponse.model_validate(ret.json())
    assert data.ok == False
    assert data.error.code == ErrorCode.INVALID_TOKEN

    # game not found
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: access_token},
    )
    assert ret.status_code == 400
    data = ErrorResponse.model_validate(ret.json())
    assert data.ok == False
    assert data.error.code == ErrorCode.GAME_NOT_FOUND

    # prepare cache and db
    async with sessionmaker() as session:
        user_repo = UserRepo(session)
        await user_repo.register(id=user_id, name=username)
        game_repo = GameRepo(session)
        game = await game_repo.create(
            game_type=GameType.MULTI, status=GameStatus.IN_GAME
        )
        game_id = game.id
        await session.commit()

    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_cache_repo.add_player(
        game_id=game_id, user_info=LobbyUserInfo(id=user_id, name=username)
    )
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_cache_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
    )

    # success
    statistics = GameStatistics(game_id=game_id, wpm=123, wpm_raw=200, acc=60)
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: access_token},
    )
    assert ret.status_code == 200
    data = SuccessResponse.model_validate(ret.json())
    assert data.ok == True

    ret = await game_cache_repo.get_players(game_id)
    assert ret
    user_info = ret[user_id]
    assert user_info.id == user_id
    assert user_info.name == username
    assert user_info.finished
    assert user_info.rank == 1
    assert user_info.wpm == statistics.wpm
    assert user_info.wpm_raw == statistics.wpm_raw
    assert user_info.acc == statistics.acc


@pytest.mark.asyncio
async def test_game_write_statistics_guest(
    client: AsyncClient,
    setting: Setting,
    redis_conn: Redis,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    game_id = 123
    user_id = "123"
    username = "123-name"
    statistics = GameStatistics(game_id=game_id, wpm=123, wpm_raw=200, acc=60)
    access_token = TokenGenerator(setting).gen_access_token(
        user_id=user_id, username=username, user_type=UserType.GUEST
    )

    # bad token
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: "qqq.bbb.ccc"},
    )
    assert ret.status_code == 400
    data = ErrorResponse.model_validate(ret.json())
    assert data.ok == False
    assert data.error.code == ErrorCode.INVALID_TOKEN

    # game not found
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: access_token},
    )
    assert ret.status_code == 400
    data = ErrorResponse.model_validate(ret.json())
    assert data.ok == False
    assert data.error.code == ErrorCode.GAME_NOT_FOUND

    # prepare cache and db
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.create(
            game_type=GameType.MULTI, status=GameStatus.IN_GAME
        )
        game_id = game.id
        await session.commit()

    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    await lobby_cache_repo.add_player(
        game_id=game_id, user_info=LobbyUserInfo(id=user_id, name=username)
    )
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_cache_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
    )

    # success
    statistics = GameStatistics(game_id=game_id, wpm=123, wpm_raw=200, acc=60)
    ret = await client.post(
        f"{API_PREFIX}/game/statistics",
        json=statistics.model_dump(),
        cookies={CookieNames.ACCESS_TOKEN: access_token},
    )
    assert ret.status_code == 200
    data = SuccessResponse.model_validate(ret.json())
    assert data.ok == True

    ret = await game_cache_repo.get_players(game_id)
    assert ret
    user_info = ret[user_id]
    assert user_info.id == user_id
    assert user_info.name == username
    assert user_info.finished
    assert user_info.rank == 1
    assert user_info.wpm == statistics.wpm
    assert user_info.wpm_raw == statistics.wpm_raw
    assert user_info.acc == statistics.acc


@dataclass(slots=True)
class _UserItem:
    id: str
    name: str
    access_token: str


@pytest.mark.asyncio
async def test_game_result(
    client: AsyncClient,
    sessionmaker: async_sessionmaker[AsyncSession],
    redis_conn: Redis,
    setting: Setting,
):
    # prepare users
    token_generator = TokenGenerator(setting)
    users: list[_UserItem] = []
    for i in range(setting.game.player_limit):
        user_id = f"{i}"
        username = f"{i}-name"
        access_token = token_generator.gen_access_token(
            user_id=user_id, username=username, user_type=UserType.GUEST
        )
        users.append(_UserItem(id=user_id, name=username, access_token=access_token))

    # prepare cache and db
    async with sessionmaker() as session:
        game_repo = GameRepo(session)
        game = await game_repo.create(
            game_type=GameType.MULTI, status=GameStatus.IN_GAME
        )
        game_id = game.id
        await session.commit()

    # init lobby cache
    lobby_cache_repo = LobbyCacheRepo(redis_conn=redis_conn, setting=setting)
    for user in users:
        await lobby_cache_repo.add_player(
            game_id=game_id, user_info=LobbyUserInfo(id=user.id, name=user.name)
        )

    # init game cache
    game_cache_repo = GameCacheRepo(redis_conn=redis_conn, setting=setting)
    await game_cache_repo.populate_with_lobby_cache(
        game_id=game_id, lobby_cache_repo=lobby_cache_repo, auto_clean=True
    )

    # write statistics
    wpm = 123
    wpm_raw = 200
    acc = 60
    for user in users:
        statistics = GameStatistics(game_id=game_id, wpm=wpm, wpm_raw=wpm_raw, acc=acc)
        ret = await client.post(
            f"{API_PREFIX}/game/statistics",
            json=statistics.model_dump(),
            cookies={CookieNames.ACCESS_TOKEN: user.access_token},
        )
        assert ret.status_code == 200

    # get statistics
    ret = await client.get(f"{API_PREFIX}/game/statistics", params={"game_id": game_id})
    assert ret.status_code == 200
    data = GameResultResponse.model_validate(ret.json())
    assert data.ok == True
    assert len(data.ranking) == len(users)

    count = 1
    for user, user_result in zip(users, data.ranking):
        assert user_result.id == user.id
        assert user_result.name == user.name
        assert user_result.finished
        assert user_result.rank == count
        assert user_result.wpm == wpm
        assert user_result.wpm_raw == wpm_raw
        assert user_result.acc == acc

        count += 1
