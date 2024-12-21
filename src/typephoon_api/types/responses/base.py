from pydantic import BaseModel, Field

from ..common import ErrorContent


class SuccessResponse(BaseModel):
    result: bool = True


class ErrorResponse(BaseModel):
    result: bool = False
    error: ErrorContent = Field(default_factory=ErrorContent)
