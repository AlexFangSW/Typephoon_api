from dataclasses import dataclass
from pydantic import BaseModel

from .enums import ErrorCode


class ErrorContext(BaseModel):
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    message: str = ""


@dataclass(slots=True)
class LobbyUserInfo:
    id: str
    name: str
    finish: bool = False
