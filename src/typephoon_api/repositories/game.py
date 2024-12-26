from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..types.enums import GameStatus

from ..orm.game import Game


class GameRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self) -> Game:
        ...

    async def get_one(self,
                      status: GameStatus,
                      lock: bool = False) -> Game | None:
        ...

    async def add_player(self):
        """Add player count by 1"""
        ...
