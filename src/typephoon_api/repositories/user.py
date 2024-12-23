from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..types.enums import UserType

from ..orm.user import User


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, id: str, name: str, user_type: UserType):
        query = insert(User).values({
            "id": id,
            "name": name,
            "user_type": user_type
        }).on_conflict_do_nothing(index_elements=["id"])

        await self._session.execute(query)

    async def get(self, id: str) -> User | None:
        query = select(User).where(User.id == id)
        return await self._session.scalar(query)
