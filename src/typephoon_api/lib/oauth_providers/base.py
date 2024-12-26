from dataclasses import dataclass
from typing import Protocol

from fastapi.datastructures import URL


@dataclass(slots=True)
class VerifyTokenRet:
    ok: bool
    user_id: str | None = None
    username: str | None = None


class OAuthProvider(Protocol):

    async def get_authorization_url(self) -> URL:
        ...

    async def handle_authorization_response(self, state: str,
                                            code: str) -> VerifyTokenRet:
        ...
