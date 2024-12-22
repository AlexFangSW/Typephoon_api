from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from ..types.enums import UserType

from ..orm.user import User


class UserRepo:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def token_upsert(self, id: str, name: str, refresh_token: str,
                           type: UserType):
        """
        Register user if needed and set refresh token
        """
        query = insert(User).values(id=id,
                                    name=name,
                                    refresh_token=refresh_token,
                                    type=type).on_conflict_do_update(
                                        index_elements="id",
                                        set_={
                                            id: id,
                                            name: name,
                                            refresh_token: refresh_token,
                                            type: type
                                        }).returning(User)

        await self._session.execute(query)
