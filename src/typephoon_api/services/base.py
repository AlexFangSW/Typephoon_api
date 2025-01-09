from pydantic import BaseModel, ConfigDict

from ..types.common import ErrorContext


class ServiceRet[T](BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    error: ErrorContext | None = None
    data: T | None = None
