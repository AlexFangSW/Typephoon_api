from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..orm.user import User


class TokenRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def set_refresh_token(self, user_id: str, refresh_token: str):
        query = update(User).values({
            "refresh_token": refresh_token
        }).where(User.id == user_id)
        await self._session.execute(query)

    async def remove_refresh_token(self, user_id: str):
        query = update(User).values({
            "refresh_token": None
        }).where(User.id == user_id)
        await self._session.execute(query)

    async def get_refresh_token(self, user_id: str) -> str | None:
        query = select(User.refresh_token).where(User.id == user_id)
        return await self._session.scalar(query)
