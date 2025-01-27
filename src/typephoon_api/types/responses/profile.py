from pydantic import Field

from ...repositories.game_result import GameResultWithGameType


from .base import SuccessResponse


class ProfileStatisticsResponse(SuccessResponse):
    """
    Attrubutes:
    - Total Games
    - Best WPM
    - Average WPM of last 10 games
    - Average WPM of all games
    """

    total_games: int = 0
    best: float = 0
    last_10: float = 0
    average: float = 0


class ProfileGraphResponse(SuccessResponse):
    data: list[GameResultWithGameType] = Field(default_factory=list)


class ProfileHistoryResponse(SuccessResponse):
    total: int
    has_prev_page: bool
    has_next_page: bool
    data: list[GameResultWithGameType] = Field(default_factory=list)
