from datetime import datetime
from pydantic import BaseModel


class Game(BaseModel):
    id: int
    created_at: datetime
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: int
    invite_token: str | None = None
    type: int
