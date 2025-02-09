from unittest.mock import AsyncMock
import pytest
from ...lib.background_tasks.lobby import LobbyBG, LobbyBGMsg, LobbyBGMsgEvent
from ..helper import *
from asyncio import sleep


@pytest.mark.asyncio
async def test_lobby_background():
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()

    user_id = "123"
    bg = LobbyBG(ws=ws, user_id=user_id)
    await bg.start()

    msg = LobbyBGMsg(event=LobbyBGMsgEvent.USER_JOINED)
    await bg._send(msg)

    assert ws.send_text.called
    assert ws.send_text.call_args.args[0] == msg.slim_dump_json()

    msg = LobbyBGMsg(event=LobbyBGMsgEvent.USER_LEFT, user_id=user_id)
    await bg._send(msg)
    assert ws.close.called

    await bg.stop()
    await sleep(0.001)
