from __future__ import annotations

from enum import StrEnum
from logging import getLogger
from typing import Type

from fastapi import WebSocket

from ...types.log import TRACE
from .base import BG, BGMsg

logger = getLogger(__name__)


class LobbyBGMsgEvent(StrEnum):
    PING = "PING"
    PONG = "PONG"
    RECONNECT = "RECONNECT"

    INIT = "INIT"
    USER_JOINED = "USER_JOINED"
    USER_LEFT = "USER_LEFT"
    GET_TOKEN = "GET_TOKEN"
    GAME_START = "GAME_START"


class LobbyBGMsg(BGMsg[LobbyBGMsgEvent]):
    guest_token_key: str | None = None
    user_id: str | None = None


class LobbyBG(BG[LobbyBGMsg]):
    def __init__(
        self,
        ws: WebSocket,
        user_id: str,
        game_id: int,
        msg_type: Type[LobbyBGMsg] = LobbyBGMsg,
    ) -> None:
        super().__init__(ws, msg_type, user_id, game_id)

    async def _recv(self, msg: LobbyBGMsg):
        logger.log(TRACE, "recv msg: %s", msg)

    async def _send(self, msg: LobbyBGMsg):
        """
        send lobby events to user
        """
        logger.log(TRACE, "send msg: %s", msg)
        if msg.event == LobbyBGMsgEvent.USER_LEFT and msg.user_id == self._user_id:
            logger.debug("stop bg, user_id: %s", self._user_id)
            await self.stop()
            return

        await self._ws.send_text(msg.slim_dump_json())
