from enum import StrEnum
from pydantic import BaseModel


class GameNotifyType(StrEnum):
    KEY_STROKE = "KEY_STROKE"


class GameNotifyMsg(BaseModel):
    notify_type: GameNotifyType
    game_id: int
    user_id: str

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)


class LobbyNotifyType(StrEnum):
    INIT = "INIT"
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"
    GET_TOKEN = "GET_TOKEN"
    GAME_START = "GAME_START"
    RECONNECT = "RECONNECT"


class LobbyNotifyMsg(BaseModel):
    notify_type: LobbyNotifyType
    game_id: int
    user_id: str | None = None

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)


class LobbyCountdownMsg(BaseModel):
    """
    This message is basically a trigger to let the server
    know when to start the game.
    """
    game_id: int
