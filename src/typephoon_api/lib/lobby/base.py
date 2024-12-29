from dataclasses import dataclass

from ...types.amqp import LobbyNotifyType


@dataclass(slots=True)
class LobbyBGNotifyMsg:
    notify_type: LobbyNotifyType
    guest_token_key: str | None = None
