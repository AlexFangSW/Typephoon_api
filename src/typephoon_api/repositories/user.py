from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import UserModel


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert(self, id: str, name: str) -> UserModel:
        ...

    ...
