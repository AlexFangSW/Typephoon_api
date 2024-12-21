from pydantic import BaseModel, Field

from ..common import ErrorContext


class SuccessResponse(BaseModel):
    result: bool = True


class ErrorResponse(BaseModel):
    result: bool = False
    error: ErrorContext = Field(default_factory=ErrorContext)
