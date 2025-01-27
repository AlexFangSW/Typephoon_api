from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from ..orm.game import GameType
from ..orm.game_result import GameResult


class StatisticsRet(BaseModel):
    """
    Attrubutes:
    - Total Games
    - Best WPM
    - Average WPM of last 10 games
    - Average WPM of all games
    """

    total_games: int = 0
    best: float = 0
    last_10: float = 0
    average: float = 0


class GameResultWithGameType(BaseModel):
    game_type: GameType
    game_id: int
    wpm: float
    wpm_raw: float
    accuracy: float
    finished_at: datetime
    rank: int


class GameResultRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_games(self, user_id: str) -> int:
        query = select(func.count(GameResult.game_id)).where(
            GameResult.user_id == user_id
        )

        ret = await self._session.scalar(query)
        if ret is None:
            return 0

        return ret

    async def last_n_games_with_game_type(
        self,
        user_id: str,
        size: int = 50,
        page: int = 1,
    ) -> list[GameResultWithGameType]:
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

    async def statistics(self, user_id: str) -> StatisticsRet:
        total_cte = (
            select(
                func.count(GameResult.wpm_correct).label("total_games"),
                func.avg(GameResult.wpm_correct).label("avg_wpm"),
                func.max(GameResult.wpm_correct).label("best_wpm"),
            )
            .where(GameResult.user_id == user_id)
            .cte("total_cte")
        )
        last_10_cte = (
            select(func.avg(GameResult.wpm_correct).label("avg_10"))
            .where(GameResult.user_id == user_id)
            .limit(10)
            .cte("last_10_cte")
        )
        query = select(
            func.coalesce(total_cte.c.total_games, 0),
            func.coalesce(total_cte.c.best_wpm, 0),
            func.coalesce(total_cte.c.avg_wpm, 0),
            func.coalesce(last_10_cte.c.avg_10, 0),
        )

        ret = await self._session.execute(query)
        total_games, best_wpm, avg_wpm, avg_10 = ret.one()
        return StatisticsRet(
            total_games=total_games, best=best_wpm, last_10=avg_10, average=avg_wpm
        )

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
        query = (
            insert(GameResult)
            .values(
                {
                    "game_id": game_id,
                    "user_id": user_id,
                    "rank": rank,
                    "wpm_raw": wpm_raw,
                    "wpm_correct": wpm_currect,
                    "accuracy": accuracy,
                    "finished_at": finished_at,
                }
            )
            .returning(GameResult)
        )

        ret = await self._session.scalar(query)
        assert ret
        return ret
