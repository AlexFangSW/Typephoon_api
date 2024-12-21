from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

from ..common import ErrorContent

T = TypeVar("T")


class ServiceRet(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = True
    error: ErrorContent | None = None
    data: T | None = None
