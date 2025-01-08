from pydantic import Field
from .base import SuccessResponse


class GameCountdownResponse(SuccessResponse):
    seconds_left: float


class GameResult(SuccessResponse):
    """
    players: sorted by rank
    """
    players: list = Field(default_factory=list)
