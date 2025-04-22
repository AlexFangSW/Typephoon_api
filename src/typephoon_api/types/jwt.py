from pydantic import BaseModel

from .enums import UserType


class JWTPayload(BaseModel):
    """
    sub: user id
    """

    sub: str
    name: str
    exp: int
    nbf: int
    iat: int
    user_type: UserType
