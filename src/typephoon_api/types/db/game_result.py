from datetime import datetime
from pydantic import BaseModel


class GameResult(BaseModel):
    game_id: int
    user_id: str
    rank: int
    wpm_raw: float
    wpm_correct: float
    accuracy: float
    status: int
    finished_at: datetime
    role: int
