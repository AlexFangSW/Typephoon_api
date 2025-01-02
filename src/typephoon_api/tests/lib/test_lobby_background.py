from unittest.mock import AsyncMock
import pytest
from asyncio import sleep

from ...lib.lobby.base import LobbyBGNotifyMsg

from ...types.amqp import LobbyNotifyType

from ...lib.lobby.lobby_background import LobbyBackground
from ...types.common import LobbyUserInfo
from ..helper import *


@pytest.mark.asyncio
async def test_lobby_background():
    websocket = AsyncMock()
    websocket.send_bytes = AsyncMock()
    user_info = LobbyUserInfo(id="1", name="player_1")

    bg = LobbyBackground(websocket=websocket, user_info=user_info)
    await bg.start()

    msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED)
    await bg.notifiy(msg)

    await sleep(0.01)

    assert websocket.send_bytes.called
    assert websocket.send_bytes.call_args.args[0] == msg.slim_dump_json(
    ).encode()

    final_msg = LobbyBGNotifyMsg(notify_type=LobbyNotifyType.RECONNECT)
    await bg.stop(final_msg)

    assert websocket.send_bytes.called
    assert websocket.send_bytes.call_args.args[0] == final_msg.slim_dump_json(
    ).encode()
