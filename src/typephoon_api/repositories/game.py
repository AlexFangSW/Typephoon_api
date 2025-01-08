from datetime import UTC, datetime
from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..orm.game import Game, GameStatus, GameType


class GameRepo:

    def __init__(self, session: AsyncSession, player_limit: int = 5) -> None:
        self._session = session
        self._player_limit = player_limit

    async def get(self, id: int, lock: bool = False) -> Game | None:
        query = select(Game).where(Game.id == id)
        if lock:
            query = query.with_for_update()
        return await self._session.scalar(query)

    async def start_game(self, id: int):
        query = update(Game).values({
            "status": GameStatus.IN_GAME,
            "start_at": datetime.now(UTC)
        }).where(Game.id == id)

        await self._session.execute(query)

    async def create(self, game_type: GameType, status: GameStatus) -> Game:
        query = insert(Game).values({
            "game_type": game_type,
            "status": status
        }).returning(Game)

        ret = await self._session.scalar(query)
        assert ret

        return ret

    async def get_one_available(self, lock: bool = False) -> Game | None:
        query = select(Game).where(
            and_(
                Game.status == GameStatus.LOBBY,
                Game.player_count < self._player_limit,
            )).limit(1)

        if lock:
            query = query.with_for_update()

        return await self._session.scalar(query)

    async def is_available(self,
                           id: int,
                           lock: bool = False,
                           new_player: bool = False) -> Game | None:
        query = select(Game).where(
            and_(
                Game.status == GameStatus.LOBBY,
                Game.id == id,
            ))
        if new_player:
            query = query.where(Game.player_count < self._player_limit)
        else:
            query = query.where(Game.player_count <= self._player_limit)

        if lock:
            query = query.with_for_update()

        return await self._session.scalar(query)

    async def increase_player_count(self, id: int) -> Game | None:
        query = update(Game).where(Game.id == id).values({
            "player_count": Game.player_count + 1
        }).returning(Game)

        return await self._session.scalar(query)

    async def decrease_player_count(self, id: int) -> Game | None:
        query = update(Game).where(Game.id == id).values({
            "player_count": Game.player_count - 1
        }).returning(Game)

        return await self._session.scalar(query)
