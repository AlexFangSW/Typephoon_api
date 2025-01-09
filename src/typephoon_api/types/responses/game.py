from pydantic import Field

from .base import SuccessResponse
from ...services.game import GetResultRetItem


class GameCountdownResponse(SuccessResponse):
    seconds_left: float


class GameResultResponse(SuccessResponse):
    """
    players: sorted by rank
    """

    ranking: list[GetResultRetItem] = Field(default_factory=list)
