from pydantic import BaseModel, Field

from ..enums import ErrorCode


class SuccessResponse(BaseModel):
    result: bool = True


class ErrorContent(BaseModel):
    code: ErrorCode = ErrorCode.UNKNOWN_ERROR
    message: str = ""


class ErrorResponse(BaseModel):
    result: bool = False
    error: ErrorContent = Field(default_factory=ErrorContent)
