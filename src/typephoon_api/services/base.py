from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from ..types.common import ErrorContext

T = TypeVar("T")


class ServiceRet(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ok: bool
    error: ErrorContext | None = None
    data: T | None = None
