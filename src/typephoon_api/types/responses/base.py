from pydantic import BaseModel, Field

from ..common import ErrorContext


class SuccessResponse(BaseModel):
    ok: bool = True


class ErrorResponse(BaseModel):
    ok: bool = False
    error: ErrorContext = Field(default_factory=ErrorContext)
