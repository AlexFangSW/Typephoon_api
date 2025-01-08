from pydantic import BaseModel

from ...types.amqp import GameNotifyType


class GameBGNotifyMsg(BaseModel):
    notify_type: GameNotifyType
    game_id: int
    user_id: str

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)
