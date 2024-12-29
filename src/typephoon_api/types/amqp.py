from enum import StrEnum
from pydantic import BaseModel
from typing import Any


class LobbyNotifyType(StrEnum):
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"
    GET_TOKEN = "GET_TOKEN"
    GAME_START = "GAME_START"
    RECONNECT = "RECONNECT"


class LobbyNotifyMsg(BaseModel):
    notify_type: LobbyNotifyType
    data: Any = None
    game_id: int


class LobbyCountdownMsg(BaseModel):
    """
    This message is basically a trigger to let the server
    know when to start the game.
    """
    game_id: int
