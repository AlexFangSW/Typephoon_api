from unittest.mock import AsyncMock
import pytest

from ...lib.lobby.base import LobbyBGNotifyMsg
from ...types.amqp import LobbyNotifyMsg, LobbyNotifyType

from ...lib.lobby.lobby_manager import LobbyBackgroundManager

from ...lib.lobby.lobby_background import LobbyBackground
from ...types.common import LobbyUserInfo
from ..helper import *


@pytest.mark.asyncio
async def test_lobby_background_manager(setting: Setting):
    background_tasks: list[LobbyBackground] = []

    for i in range(setting.game.player_limit):
        user_info = LobbyUserInfo(id=f"{i}", name=f"player_{i}")
        bg = LobbyBackground(websocket=AsyncMock(), user_info=user_info)
        bg.notifiy = AsyncMock()
        bg.stop = AsyncMock()
        background_tasks.append(bg)

    bg_manager = LobbyBackgroundManager()
    for bg in background_tasks:
        await bg_manager.add(bg)
    assert len(bg_manager._background_tasks.keys()) == setting.game.player_limit

    await bg_manager.broadcast(
        msg=LobbyBGNotifyMsg(notify_type=LobbyNotifyType.USER_JOINED)
    )

    for bg in background_tasks:
        assert isinstance(bg.notifiy, AsyncMock)
        assert bg.notifiy.called

    await bg_manager.stop()

    for bg in background_tasks:
        assert isinstance(bg.stop, AsyncMock)
        assert bg.stop.called
