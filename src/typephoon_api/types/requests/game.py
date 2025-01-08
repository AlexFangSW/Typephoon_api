from pydantic import BaseModel


class GameStatistics(BaseModel):
    game_id: str
    wpm: float
    wpm_raw: float
    acc: float
    acc_raw: float
