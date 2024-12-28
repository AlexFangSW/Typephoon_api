from sqlalchemy import and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..orm.game import Game, GameStatus, GameType


class GameRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
                Game.player_count < 5,
            )).limit(1)

        if lock:
            query = query.with_for_update()

        return await self._session.scalar(query)

    async def add_player(self, id: int):
        query = update(Game).where(Game.id == id).values(
            {"player_count": Game.player_count + 1})

        return await self._session.execute(query)
