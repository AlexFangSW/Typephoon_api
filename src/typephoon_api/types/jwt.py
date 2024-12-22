from dataclasses import dataclass


@dataclass(slots=True)
class JWTPayload:
    user_id: str
