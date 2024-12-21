from pydantic import BaseModel

from .enums import ErrorCode


class ErrorContext(BaseModel):
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    message: str = ""
