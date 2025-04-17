from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..orm.game import GameType
from ..orm.game_result import GameResult


class GameResultWithGameType(BaseModel):
    game_type: GameType
    game_id: int
    wpm: float
    wpm_raw: float
    accuracy: float
    finished_at: datetime
    rank: int


class AvgLastNGamesRet(BaseModel):
    wpm_raw: float
    wpm: float
    acc: float


class GameResultRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_total_games(self, user_id: str) -> int:
        query = select(func.count(GameResult.game_id)).where(
            GameResult.user_id == user_id
        )

        ret = await self._session.scalar(query)
        if ret is None:
            return 0

        return ret

    async def get_last_n_games_with_game_type(
        self,
        user_id: str,
        size: int = 50,
        page: int = 1,
    ) -> list[GameResultWithGameType]:
        """
        Returns:
            - A list of game result ordered in descent on 'finish_ts'
        """
        query = (
            select(GameResult)
            .options(joinedload(GameResult.game))
            .where(GameResult.user_id == user_id)
            .limit(size)
            .offset((page - 1) * size)
            .order_by(GameResult.finished_at.desc())
        )
        ret = await self._session.scalars(query)

        result: list[GameResultWithGameType] = []
        for item in ret:
            result.append(
                GameResultWithGameType(
                    game_type=item.game.game_type,
                    game_id=item.game_id,
                    wpm=item.wpm_correct,
                    wpm_raw=item.wpm_raw,
                    accuracy=item.accuracy,
                    finished_at=item.finished_at,
                    rank=item.rank,
                )
            )

        return result

    async def get_best(self, user_id: str) -> GameResult | None:
        query = (
            select(GameResult)
            .where(GameResult.user_id == user_id)
            .order_by(GameResult.wpm_correct.desc())
            .limit(1)
        )
        return await self._session.scalar(query)

    async def get_avg_last_n_games(
        self, user_id: str, last_n: int | None = None
    ) -> AvgLastNGamesRet:
        """
        return the average statistics of last n games.
        Arguments:
            - user_id: user id
            - last_n: last n games to select, None equals 'ALL'
        """
        last_n_cte = select(
            GameResult.wpm_raw.label("wpm_raw"),
            GameResult.wpm_correct.label("wpm_correct"),
            GameResult.accuracy.label("accuracy"),
        ).where(GameResult.user_id == user_id)

        if last_n is not None:
            last_n_cte = last_n_cte.limit(last_n).order_by(
                GameResult.finished_at.desc()
            )

        last_n_cte = last_n_cte.cte("last_n_cte")

        query = select(
            func.coalesce(func.avg(last_n_cte.c.wpm_raw), 0),
            func.coalesce(func.avg(last_n_cte.c.wpm_correct), 0),
            func.coalesce(func.avg(last_n_cte.c.accuracy), 0),
        ).select_from(last_n_cte)

        ret = await self._session.execute(query)
        wpm_raw, wpm, acc = ret.one()
        return AvgLastNGamesRet(wpm_raw=wpm_raw, wpm=wpm, acc=acc)

    async def create(
        self,
        game_id: int,
        user_id: str,
        rank: int,
        wpm_raw: float,
        wpm_correct: float,
        accuracy: float,
        finished_at: datetime,
    ) -> GameResult:
        query = (
            insert(GameResult)
            .values(
                {
                    "game_id": game_id,
                    "user_id": user_id,
                    "rank": rank,
                    "wpm_raw": wpm_raw,
                    "wpm_correct": wpm_correct,
                    "accuracy": accuracy,
                    "finished_at": finished_at,
                }
            )
            .returning(GameResult)
        )

        ret = await self._session.scalar(query)
        assert ret
        return ret
