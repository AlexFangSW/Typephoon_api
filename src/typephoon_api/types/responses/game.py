from pydantic import Field

from ..common import GameUserInfo
from .base import SuccessResponse


class GameCountdownResponse(SuccessResponse):
    seconds_left: float


class GameResultResponse(SuccessResponse):
    """
    players: sorted by rank
    """

    ranking: list[GameUserInfo] = Field(default_factory=list)


class GamePlayersResponse(SuccessResponse):
    me: GameUserInfo
    others: dict[str, GameUserInfo] = Field(default_factory=dict)


class GameWordsResponse(SuccessResponse):
    words: str
