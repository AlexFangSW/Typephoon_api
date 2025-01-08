from pydantic import BaseModel


class GameStatistics(BaseModel):
    game_id: int
    wpm: float
    wpm_raw: float
    acc: float
    acc_raw: float
