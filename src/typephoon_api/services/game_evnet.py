from fastapi import WebSocket

from ..types.enums import WSConnectionType


class GameEventService:

    def __init__(self) -> None:
        pass

    async def process(
        self,
        websocket: WebSocket,
        connection_type: WSConnectionType,
        prev_game_id: int | None = None,
    ):
        ...

    ...
