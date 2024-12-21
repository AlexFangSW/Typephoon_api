from pydantic import BaseModel

from .enums import ErrorCode


class ErrorContent(BaseModel):
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    message: str = ""
