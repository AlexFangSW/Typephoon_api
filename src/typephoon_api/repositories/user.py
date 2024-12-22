from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import session
from sqlalchemy.sql import select

from ..types.enums import UserType

from ..orm.user import User


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def token_upsert(self, id: str, name: str, refresh_token: str,
                           user_type: UserType):
        """
        Register user if needed and set refresh token
        """
        query = insert(User).values({
            "id": id,
            "name": name,
            "refresh_token": refresh_token,
            "user_type": user_type
        }).on_conflict_do_update(
            index_elements=["id"],
            set_={"refresh_token": refresh_token},
        )

        await self._session.execute(query)

    async def get(self, id: str) -> User | None:
        query = select(User).where(User.id == id)
        return await self._session.scalar(query)
