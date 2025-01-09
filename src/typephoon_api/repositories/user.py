from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..orm.user import User


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, id: str, name: str) -> User:
        query = (
            insert(User)
            .values(
                {
                    "id": id,
                    "name": name,
                }
            )
            .on_conflict_do_update(index_elements=["id"], set_={"id": id})
            .returning(User)
        )

        user = await self._session.scalar(query)
        assert user
        return user

    async def get(self, id: str) -> User | None:
        query = select(User).where(User.id == id)
        return await self._session.scalar(query)
