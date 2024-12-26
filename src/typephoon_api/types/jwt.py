from dataclasses import dataclass

from .enums import UserType


@dataclass(slots=True)
class JWTPayload:
    """
    sub: user id
    """
    sub: str
    name: str
    exp: int
    nbf: int
    iat: int
    user_type: UserType
