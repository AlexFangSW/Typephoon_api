from pydantic import BaseModel

from ...types.amqp import LobbyNotifyType


class LobbyBGNotifyMsg(BaseModel):
    notify_type: LobbyNotifyType
    guest_token_key: str | None = None

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)
