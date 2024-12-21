from typing import Generic, TypeVar
from fastapi.datastructures import URL
from pydantic import BaseModel, ConfigDict

from ..common import ErrorContext

T = TypeVar("T")


class ServiceRet(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = True
    error: ErrorContext | None = None
    error_redirect: URL | None = None
    data: T | None = None
