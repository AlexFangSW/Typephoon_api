from pydantic import Field

from ..common import LobbyUserInfo
from .base import SuccessResponse


class LobbyPlayersResponse(SuccessResponse):
    me: LobbyUserInfo | None = None
    others: list[LobbyUserInfo] = Field(default_factory=list)


class LobbyCountdownResponse(SuccessResponse):
    seconds_left: float
