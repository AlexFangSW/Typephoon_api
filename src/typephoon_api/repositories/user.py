from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import select

from ..lib.util import gen_user_id

from ..types.enums import LoginMethods

from ..orm.user import User


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register_with_google(self, id: str, name: str) -> User:
        id = gen_user_id(id, LoginMethods.GOOGLE)
        return await self.register(id=id, name=name)

    async def register(self, id: str, name: str) -> User:
        query = insert(User).values({
            "id": id,
            "name": name,
        }).on_conflict_do_update(index_elements=["id"], set_={
            "id": id
        }).returning(User)

        user = await self._session.scalar(query)
        assert user
        return user

    async def get(self, id: str) -> User | None:
        query = select(User).where(User.id == id)
        return await self._session.scalar(query)
