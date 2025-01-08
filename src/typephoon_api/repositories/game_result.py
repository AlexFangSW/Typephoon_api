from datetime import datetime
from os import access

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from ..orm.game_result import GameResult


class GameResultRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        game_id: int,
        user_id: str,
        rank: int,
        wpm_raw: float,
        wpm_currect: float,
        accuracy: float,
        finished_at: datetime,
    ) -> GameResult:
        query = insert(GameResult).values({
            "game_id": game_id,
            "user_id": user_id,
            "rank": rank,
            "wpm_raw": wpm_raw,
            "wpm_correct": wpm_currect,
            'accuracy': accuracy,
            "finished_at": finished_at,
        }).returning(GameResult)

        ret = await self._session.scalar(query)
        assert ret
        return ret
