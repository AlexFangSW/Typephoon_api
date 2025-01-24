from pydantic import Field

from ...services.profile import GameResultItem

from .base import SuccessResponse


class ProfileStatisticsResponse(SuccessResponse):
    """
    Attrubutes:
    - Best WPM
    - Average WPM of last 10 games
    - Average WPM of all games
    """

    best: float = 0
    last_10: float = 0
    average: float = 0


class ProfileGraphResponse(SuccessResponse):
    data: list[GameResultItem] = Field(default_factory=list)


class ProfileHistoryResponse(SuccessResponse):
    total: int
    has_prev_page: bool
    has_next_page: bool
    data: list[GameResultItem] = Field(default_factory=list)
