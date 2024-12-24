from dataclasses import dataclass


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
