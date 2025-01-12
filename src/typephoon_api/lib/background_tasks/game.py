from __future__ import annotations
from enum import StrEnum
from logging import getLogger
from typing import Type
from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractConnection
from fastapi import WebSocket
from pamqp.commands import Basic

from ...types.errors import PublishNotAcknowledged

from ...types.amqp import KeystrokeHeader, KeystrokeMsg

from ...types.setting import Setting
from .base import BG, BGMsg

logger = getLogger(__name__)


class GameBGMsgEvent(StrEnum):
    PING = "PING"
    PONG = "PONG"
    RECONNECT = "RECONNECT"

    KEY_STOKE = "KEY_STOKE"


class GameBGMsg(BGMsg[GameBGMsgEvent]):
    word_index: int | None = None
    char_index: int | None = None


# TODO: actually use it
class GameBG(BG[GameBGMsg]):
    def __init__(
        self,
        ws: WebSocket,
        msg_type: Type[GameBGMsg],
        user_id: str,
        amqp_conn: AbstractConnection,
        setting: Setting,
        game_id: int,
        server_name: str,
    ) -> None:
        super().__init__(ws, msg_type, user_id)
        self._amqp_conn = amqp_conn
        self._setting = setting
        self._game_id = game_id
        self._server_name = server_name

    async def _recv(self, msg: GameBGMsg):
        """
        receive key stroks from player and broadcast to all
        players in the same game
        """
        if msg.event == GameBGMsgEvent.KEY_STOKE:
            logger.debug("broadcast keystroke, %s", msg)

            assert msg.word_index
            assert msg.char_index

            keystroke_msg = KeystrokeMsg(
                game_id=self._game_id,
                user_id=self._user_id,
                word_index=msg.word_index,
                char_index=msg.char_index,
            )

            amqp_msg = Message(
                body=keystroke_msg.model_dump_json().encode(),
                headers=KeystrokeHeader(source=self._server_name).model_dump(),
                delivery_mode=DeliveryMode.PERSISTENT,
            )

            confirm = await self._exchange.publish(message=amqp_msg, routing_key="")
            if not isinstance(confirm, Basic.Ack):
                raise PublishNotAcknowledged("keystroke publish not asknowledged")

    async def _send(self, msg: GameBGMsg):
        """
        send key stroks from other player to user
        """
        logger.debug("got msg: %s", msg)
        await self._ws.send_bytes(msg.slim_dump_json().encode())

    async def start(self, init_msg: GameBGMsg | None = None):
        self._channel = await self._amqp_conn.channel()
        self._exchange = await self._channel.get_exchange(
            self._setting.amqp.game_keystroke_fanout_exchange
        )
        return await super().start(init_msg)

    async def stop(self, final_msg: GameBGMsg | None = None):
        await self._channel.close()
        return await super().stop(final_msg)
