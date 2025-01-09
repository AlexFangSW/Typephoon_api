from pydantic import BaseModel

from ...types.amqp import GameNotifyType


class GameBGNotifyMsg(BaseModel):
    notify_type: GameNotifyType
    user_id: str | None = None
    word_index: int | None = None
    char_index: int | None = None

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)
