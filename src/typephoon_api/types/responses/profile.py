from pydantic import Field

from ...repositories.game_result import GameResultWithGameType


from .base import SuccessResponse


class ProfileStatisticsResponse(SuccessResponse):
    total_games: int

    wpm_best: float
    acc_best: float

    wpm_avg_10: float
    acc_avg_10: float

    wpm_avg_all: float
    acc_avg_all: float


class ProfileGraphResponse(SuccessResponse):
    data: list[GameResultWithGameType] = Field(default_factory=list)


class ProfileHistoryResponse(SuccessResponse):
    total: int
    has_prev_page: bool
    has_next_page: bool
    data: list[GameResultWithGameType] = Field(default_factory=list)
