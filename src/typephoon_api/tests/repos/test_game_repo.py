import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ...orm.game import Game, GameStatus, GameType

from ...repositories.game import GameRepo
from ..helper import *


@pytest.mark.asyncio
async def test_game_repo_create(sessionmaker: async_sessionmaker[AsyncSession]):
    async with sessionmaker() as session:
        repo = GameRepo(session=session)

        game = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        assert game.id is not None
        assert game.game_type == GameType.MULTI
        assert game.status == GameStatus.LOBBY

        game_id = game.id

        await session.commit()

    async with sessionmaker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.id == game_id
        assert game.game_type == GameType.MULTI
        assert game.status == GameStatus.LOBBY
        assert game.player_count == 0
        assert game.finish_count == 0


@pytest.mark.asyncio
async def test_game_repo_player_count(sessionmaker: async_sessionmaker[AsyncSession]):
    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        game_id = game.id
        await repo.increase_player_count(game_id)
        await repo.increase_player_count(game_id)
        await session.commit()

    async with sessionmaker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.player_count == 2

    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        await repo.decrease_player_count(game_id)
        await session.commit()

    async with sessionmaker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.player_count == 1


@pytest.mark.asyncio
async def test_game_repo_is_available(sessionmaker: async_sessionmaker[AsyncSession]):

    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        game_id = game.id
        await repo.increase_player_count(game_id)
        await repo.increase_player_count(game_id)
        await repo.increase_player_count(game_id)
        await repo.increase_player_count(game_id)
        await repo.increase_player_count(game_id)
        await session.commit()

    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.is_available(game_id)
        assert game is not None
        assert game.player_count == 5

        game = await repo.is_available(game_id, new_player=True)
        assert game is None


@pytest.mark.asyncio
async def test_game_repo_get_one_available(
    sessionmaker: async_sessionmaker[AsyncSession],
):
    async with sessionmaker() as session:
        repo = GameRepo(session=session)

        game_full = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        for _ in range(repo._player_limit):
            await repo.increase_player_count(game_full.id)

        game_available = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        game_available_id = game_available.id

        await session.commit()
        await session.refresh(game_available)

    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.get_one_available()
        assert game is not None
        assert game.id == game_available_id
        assert game.player_count == 0


@pytest.mark.asyncio
async def test_game_repo_start_game(sessionmaker: async_sessionmaker[AsyncSession]):
    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.create(GameType.MULTI, GameStatus.LOBBY)
        game_id = game.id
        await repo.start_game(game_id)
        await session.commit()

    async with sessionmaker() as session:
        repo = GameRepo(session=session)
        game = await repo.get(game_id)
        assert game is not None
        assert game.status == GameStatus.IN_GAME
        assert game.start_at is not None
