from typing import Self
from pydantic import BaseModel

from .enums import ErrorCode


class ErrorContext(BaseModel):
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    message: str = ""


class LobbyUserInfo(BaseModel):
    id: str
    name: str


class GameUserInfo(BaseModel):
    """
    - finished: ISO 8061 format timestamp
    """

    id: str
    name: str

    # populate after finish
    finished: str | None = None
    rank: int = -1
    wpm: float | None = None
    wpm_raw: float | None = None
    acc: float | None = None

    @classmethod
    def from_lobby_cache(cls, inpt: LobbyUserInfo) -> Self:
        return cls(id=inpt.id, name=inpt.name)
