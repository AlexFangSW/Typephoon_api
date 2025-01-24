from datetime import datetime

from pydantic import BaseModel, Field

from ..common import GameTypeStr
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


class ProfileGameResult(BaseModel):
    game_id: int
    wpm: float
    wpm_raw: float
    accuracy: float
    finished_at: datetime
    rank: int


class ProfileGraphItem(ProfileGameResult):
    pass


class ProfileGraphResponse(SuccessResponse):
    data: list[ProfileGraphItem] = Field(default_factory=list)


class ProfileHistoryItem(ProfileGameResult):
    game_type: GameTypeStr


class ProfileHistoryResponse(SuccessResponse):
    data: list[ProfileHistoryItem] = Field(default_factory=list)
