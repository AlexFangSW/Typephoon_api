from enum import StrEnum
from pydantic import BaseModel

from ..lib.background_tasks.lobby import LobbyBGMsgEvent


class GameNotifyType(StrEnum):
    KEY_STROKE = "KEY_STROKE"
    RECONNECT = "RECONNECT"


class KeystrokeHeader(BaseModel):
    """
    source: server name
    """

    source: str | None = None


class KeystrokeMsg(BaseModel):
    game_id: int
    user_id: str
    word_index: int
    char_index: int


class LobbyNotifyMsg(BaseModel):
    notify_type: LobbyBGMsgEvent
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
