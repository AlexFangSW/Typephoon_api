from datetime import timedelta
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from statistics import mean

from ...orm.game import GameStatus, GameType
from ...repositories.game import GameRepo

from ...repositories.game_result import GameResultRepo, GameResultWithGameType

from ...repositories.user import UserRepo

from ...types.responses.profile import (
    ProfileGraphResponse,
    ProfileHistoryResponse,
    ProfileStatisticsResponse,
)

from ...types.enums import CookieNames, UserType

from ...lib.token_generator import TokenGenerator

from ..helper import *


@pytest.mark.asyncio
async def test_api_profile_statistics_guest(client: AsyncClient, setting: Setting):
    # guest
    token_generator = TokenGenerator(setting)
    guest_token = token_generator.gen_access_token(
        user_id="guest-id", username="guest-name", user_type=UserType.GUEST
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/statistics",
        cookies={CookieNames.ACCESS_TOKEN: guest_token},
    )
    assert ret.status_code == 200
    ret_data = ProfileStatisticsResponse.model_validate(ret.json())
    assert ret_data == ProfileStatisticsResponse(
        total_games=0,
        wpm_best=0,
        acc_best=0,
        wpm_avg_10=0,
        acc_avg_10=0,
        wpm_avg_all=0,
        acc_avg_all=0,
    )


@pytest.mark.asyncio
async def test_api_profile_statistics(
    client: AsyncClient,
    setting: Setting,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    # prepare data
    user_id = "dummy-id"
    username = "dummy-username"
    games: list[dict] = []
    for i in range(20):
        games.append(
            {
                "game_id": -1,
                "user_id": user_id,
                "rank": 1,
                "wpm_raw": (i + 2) * 10,
                "wpm_correct": (i + 1) * 10,
                "accuracy": 100 - i,
                "finished_at": NOW + timedelta(minutes=i),
            }
        )

    # answers
    wpm_best_answer = games[-1]["wpm_correct"]
    acc_best_answer = games[-1]["accuracy"]

    wpm_avg_10_answer = mean([i["wpm_correct"] for i in games[-10:]])
    acc_avg_10_answer = mean([i["accuracy"] for i in games[-10:]])

    wpm_avg_all_answer = mean([i["wpm_correct"] for i in games])
    acc_avg_all_answer = mean([i["accuracy"] for i in games])

    async with sessionmaker() as session:
        user_repo = UserRepo(session)
        game_result_repo = GameResultRepo(session)
        game_repo = GameRepo(session)
        await user_repo.register(id=user_id, name=username)
        for game in games:
            new_game = await game_repo.create(
                game_type=GameType.MULTI, status=GameStatus.FINISHED
            )
            game["game_id"] = new_game.id
            await game_result_repo.create(**game)

        await session.commit()

    token_generator = TokenGenerator(setting)
    token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/statistics",
        cookies={CookieNames.ACCESS_TOKEN: token},
    )
    assert ret.status_code == 200
    ret_data = ProfileStatisticsResponse.model_validate(ret.json())
    assert ret_data == ProfileStatisticsResponse(
        total_games=len(games),
        wpm_best=wpm_best_answer,
        acc_best=acc_best_answer,
        wpm_avg_10=wpm_avg_10_answer,
        acc_avg_10=acc_avg_10_answer,
        wpm_avg_all=wpm_avg_all_answer,
        acc_avg_all=acc_avg_all_answer,
    )


@pytest.mark.asyncio
async def test_api_profile_graph_guest(
    client: AsyncClient,
    setting: Setting,
):
    token_generator = TokenGenerator(setting)
    token = token_generator.gen_access_token(
        user_id="guest-id", username="guest-username", user_type=UserType.GUEST
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/graph",
        cookies={CookieNames.ACCESS_TOKEN: token},
        params={"size": 10},
    )
    assert ret.status_code == 200
    ret_data = ProfileGraphResponse.model_validate(ret.json())
    assert ret_data.data == []


@pytest.mark.asyncio
async def test_api_profile_graph(
    client: AsyncClient,
    setting: Setting,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    # prepare data
    user_id = "dummy-id"
    username = "dummy-username"
    games: list[GameResultWithGameType] = []
    for i in range(20):
        games.append(
            GameResultWithGameType(
                game_type=GameType.MULTI,
                game_id=-1,
                rank=1,
                wpm_raw=(i + 2) * 10,
                wpm=(i + 1) * 10,
                accuracy=100 - i,
                finished_at=NOW + timedelta(minutes=i),
            )
        )

    async with sessionmaker() as session:
        user_repo = UserRepo(session)
        game_result_repo = GameResultRepo(session)
        game_repo = GameRepo(session)
        await user_repo.register(id=user_id, name=username)
        for game in games:
            new_game = await game_repo.create(
                game_type=game.game_type, status=GameStatus.FINISHED
            )
            game.game_id = new_game.id
            await game_result_repo.create(
                game_id=game.game_id,
                user_id=user_id,
                rank=1,
                wpm_raw=game.wpm_raw,
                wpm_correct=game.wpm,
                accuracy=game.accuracy,
                finished_at=game.finished_at,
            )

        await session.commit()

    token_generator = TokenGenerator(setting)
    token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/graph",
        cookies={CookieNames.ACCESS_TOKEN: token},
        params={"size": 10},
    )
    assert ret.status_code == 200
    ret_data = ProfileGraphResponse.model_validate(ret.json())
    assert ret_data.data == games[-10:]


@pytest.mark.asyncio
async def test_api_profile_history_guest(
    client: AsyncClient,
    setting: Setting,
):
    token_generator = TokenGenerator(setting)
    token = token_generator.gen_access_token(
        user_id="guest-id", username="guest-username", user_type=UserType.GUEST
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/history",
        cookies={CookieNames.ACCESS_TOKEN: token},
        params={"size": 10, "page": 2},
    )
    assert ret.status_code == 200
    ret_data = ProfileHistoryResponse.model_validate(ret.json())
    assert ret_data.total == 0
    assert ret_data.has_prev_page is False
    assert ret_data.has_next_page is False
    assert ret_data.data == []


@pytest.mark.asyncio
async def test_api_profile_history(
    client: AsyncClient,
    setting: Setting,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    # prepare data
    user_id = "dummy-id"
    username = "dummy-username"
    games: list[GameResultWithGameType] = []
    for i in range(30):
        games.append(
            GameResultWithGameType(
                game_type=GameType.MULTI,
                game_id=-1,
                rank=1,
                wpm_raw=(i + 2) * 10,
                wpm=(i + 1) * 10,
                accuracy=100 - i,
                finished_at=NOW + timedelta(minutes=i),
            )
        )

    async with sessionmaker() as session:
        user_repo = UserRepo(session)
        game_result_repo = GameResultRepo(session)
        game_repo = GameRepo(session)
        await user_repo.register(id=user_id, name=username)
        for game in games:
            new_game = await game_repo.create(
                game_type=game.game_type, status=GameStatus.FINISHED
            )
            game.game_id = new_game.id
            await game_result_repo.create(
                game_id=game.game_id,
                user_id=user_id,
                rank=1,
                wpm_raw=game.wpm_raw,
                wpm_correct=game.wpm,
                accuracy=game.accuracy,
                finished_at=game.finished_at,
            )

        await session.commit()

    token_generator = TokenGenerator(setting)
    token = token_generator.gen_access_token(
        user_id=user_id, username=username, user_type=UserType.REGISTERED
    )
    ret = await client.get(
        f"{API_PREFIX}/profile/history",
        cookies={CookieNames.ACCESS_TOKEN: token},
        params={"size": 10, "page": 2},
    )
    assert ret.status_code == 200
    ret_data = ProfileHistoryResponse.model_validate(ret.json())
    assert ret_data.total == len(games)
    assert ret_data.has_prev_page is True
    assert ret_data.has_next_page is True
    assert len(ret_data.data) == 10
    assert ret_data.data == sorted(
        games[10:20], key=lambda x: x.finished_at, reverse=True
    )
