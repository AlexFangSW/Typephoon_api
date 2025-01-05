from pydantic import Field
from .base import SuccessResponse

from ..common import LobbyUserInfo


class LobbyPlayersResponse(SuccessResponse):
    me: LobbyUserInfo | None = None
    others: list[LobbyUserInfo] = Field(default_factory=list)


class LobbyCountdownResponse(SuccessResponse):
    seconds_left: float
