from pydantic import BaseModel
from datetime import datetime


class User(BaseModel):
    id: str
    name: str
    registered_at: datetime
    type: int
