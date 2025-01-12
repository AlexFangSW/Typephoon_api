from asyncio import Queue, sleep
from typing import Type

from fastapi import WebSocket
from ...lib.background_tasks.base import (
    BG,
    BGGroup,
    BGManager,
    BGMsg,
    BGMsgEvent,
    _BGMsgEvent,
    _BGMsg,
)
from ..helper import *
from unittest.mock import AsyncMock
import pytest


@pytest.mark.asyncio
async def test_bg_manager_get():
    class DummyBG[T: BGMsg](BG[T]):
        async def _send(self, msg: T):
            pass

        async def _recv(self, msg: T):
            pass

    game_id = 123
    bg_manager = BGManager[BGMsg, DummyBG](msg_type=BGMsg, bg_type=DummyBG)
    await bg_manager.start()

    bg_group = await bg_manager.get(game_id)
    assert bg_group is await bg_manager.get(game_id)

    assert bg_manager._group_bucket[game_id]

    await bg_manager.stop()


@pytest.mark.asyncio
async def test_bg_manager_remove():
    class DummyBG[T: BGMsg](BG[T]):
        async def _send(self, msg: T):
            pass

        async def _recv(self, msg: T):
            pass

    game_id = 123
    ping = BGMsg(event=BGMsgEvent.PING)
    bg_manager = BGManager[BGMsg, DummyBG](msg_type=BGMsg, bg_type=DummyBG)
    await bg_manager.start()

    bg_group = await bg_manager.get(game_id)
    bg_group.stop = AsyncMock()
    await bg_manager.remove(game_id=game_id, final_msg=ping)
    assert bg_group.stop.called
    assert bg_group.stop.call_args.args == (ping,)

    await bg_manager.stop()


@pytest.mark.asyncio
async def test_bg_manager_manage_loop():
    class DummyBG[T: BGMsg](BG[T]):
        async def _send(self, msg: T):
            pass

        async def _recv(self, msg: T):
            pass

    game_id = 123
    user_id = "123"
    bg_manager = BGManager[BGMsg, DummyBG](msg_type=BGMsg, bg_type=DummyBG)
    await bg_manager.start()

    bg_group = await bg_manager.get(game_id)
    await bg_group.add(user_id=user_id, ws= AsyncMock())

    # none existing game
    await bg_manager._queue.put(
        _BGMsg(game_id=9999, user_id=user_id, event=_BGMsgEvent.UPDATE)
    )

    # make sure it doesn't wrongly remove
    await bg_manager._queue.put(
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.UPDATE)
    )
    await sleep(0.01)
    assert bg_manager._group_bucket[game_id].connections == 1

    # healthcheck fail removes one connection, total connectoins left is 0,
    # the bg_group is removed.
    await bg_manager._queue.put(
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.HEALTHCHECK_FAIL)
    )
    await sleep(0.01)
    assert bg_manager._group_bucket.get(game_id) is None

    await bg_manager.stop()


@pytest.mark.asyncio
async def test_bg_manager_stop():
    class DummyBG[T: BGMsg](BG[T]):
        async def _send(self, msg: T):
            pass

        async def _recv(self, msg: T):
            pass

    games = [111, 222]
    bg_manager = BGManager[BGMsg, DummyBG](msg_type=BGMsg, bg_type=DummyBG)
    ping = BGMsg(event=BGMsgEvent.PING)
    await bg_manager.start()

    bg_groups: list[BGGroup] = []
    for game_id in games:
        group = await bg_manager.get(game_id)
        group.stop = AsyncMock()
        bg_groups.append(group)

    await bg_manager.stop(ping)

    assert bg_manager._group_bucket == {}

    for group in bg_groups:
        assert group.stop.called  # type: ignore
        assert group.stop.call_args.args == (ping,)  # type: ignore


@pytest.mark.asyncio
async def test_bg_group_add():
    class DummyBG[T: BGMsg](BG[T]):
        send_history: list[T] = []

        async def _send(self, msg: T):
            self.send_history.append(msg)

        async def _recv(self, msg: T):
            pass

    queue = Queue()
    game_id = 123
    user_id = "123"
    ws = AsyncMock()
    ping = BGMsg(event=BGMsgEvent.PING)

    bg_group = BGGroup[BGMsg, DummyBG](
        queue=queue, game_id=game_id, msg_type=BGMsg, bg_type=DummyBG
    )

    await bg_group.add(user_id=user_id, ws=ws, init_msg=ping)

    await sleep(0.01)

    # message sent to manager
    assert queue.qsize() == 1
    msg = await queue.get()
    assert msg == _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.UPDATE)

    # health check loop
    health_check_task = bg_group._healthcheck_bucket[user_id]
    assert not health_check_task.done()

    bg = bg_group._bg_bucket[user_id]
    # health check + init msg
    assert len(bg.send_history) == 2

    await bg_group.stop()


@pytest.mark.asyncio
async def test_bg_group_healthcheck_fail():
    class DummyBG[T: BGMsg](BG[T]):

        async def _send(self, msg: T):
            pass

        async def _recv(self, msg: T):
            pass

        async def ping(self):
            raise RuntimeError("intentional error")

    queue = Queue()
    game_id = 123
    user_id = "123"

    bg_group = BGGroup[BGMsg, DummyBG](
        queue=queue, game_id=game_id, msg_type=BGMsg, bg_type=DummyBG
    )

    await bg_group.add(user_id=user_id, ws=AsyncMock())

    await sleep(0.01)

    # send disconnect msg to manager when healthcheck fails
    assert queue.qsize() == 2
    queue_msg: list[_BGMsg] = []
    for _ in range(2):
        msg = await queue.get()
        queue_msg.append(msg)

    assert queue_msg == [
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.UPDATE),
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.HEALTHCHECK_FAIL),
    ]

    await bg_group.stop()


@pytest.mark.asyncio
async def test_bg_group_remove():
    class DummyBG[T: BGMsg](BG[T]):
        send_history: list[T] = []

        async def _send(self, msg: T):
            self.send_history.append(msg)

        async def _recv(self, msg: T):
            pass

    queue = Queue()
    game_id = 123
    user_id = "123"
    pong = BGMsg(event=BGMsgEvent.PONG)

    bg_group = BGGroup[BGMsg, DummyBG](
        queue=queue, game_id=game_id, msg_type=BGMsg, bg_type=DummyBG
    )

    await bg_group.add(user_id=user_id, ws=AsyncMock())
    bg = bg_group._bg_bucket[user_id]
    await bg_group.remove(user_id=user_id, final_msg=pong)

    # should be fine to call on none existing user
    await bg_group.remove(user_id=user_id, final_msg=pong)
    await bg_group.remove(user_id=user_id, final_msg=pong)

    await sleep(0.01)

    assert bg_group._healthcheck_bucket.get(user_id) is None
    assert bg_group._bg_bucket.get(user_id) is None

    assert len(bg.send_history) == 1

    assert bg_group._queue.qsize() == 2
    queue_msg: list[_BGMsg] = []
    for _ in range(2):
        msg = await queue.get()
        queue_msg.append(msg)

    assert queue_msg == [
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.UPDATE),
        _BGMsg(game_id=game_id, user_id=user_id, event=_BGMsgEvent.UPDATE),
    ]

    await bg_group.stop()


@pytest.mark.asyncio
async def test_bg_group_broadcast():
    class DummyBG[T: BGMsg](BG[T]):
        def __init__(self, ws: WebSocket, msg_type: Type[T]) -> None:
            super().__init__(ws, msg_type)
            self.send_history: list[T] = []

        async def _send(self, msg: T):
            self.send_history.append(msg)

        async def _recv(self, msg: T):
            pass

    queue = Queue()
    game_id = 123
    users = ["111", "222"]
    ping = BGMsg(event=BGMsgEvent.PING)

    bg_group = BGGroup[BGMsg, DummyBG](
        queue=queue, game_id=game_id, msg_type=BGMsg, bg_type=DummyBG
    )

    for user_id in users:
        await bg_group.add(user_id=user_id, ws=AsyncMock())
    await bg_group.broadcast(ping)

    await sleep(0.01)

    for user_id in users:
        bg = bg_group._bg_bucket[user_id]
        assert len(bg.send_history) == 2

    await bg_group.stop()


@pytest.mark.asyncio
async def test_bg_group_stop():
    class DummyBG[T: BGMsg](BG[T]):
        def __init__(self, ws: WebSocket, msg_type: Type[T]) -> None:
            super().__init__(ws, msg_type)
            self.send_history: list[T] = []

        async def _send(self, msg: T):
            self.send_history.append(msg)

        async def _recv(self, msg: T):
            pass

    queue = Queue()
    game_id = 123
    users = ["111", "222"]
    ping = BGMsg(event=BGMsgEvent.PING)

    bg_group = BGGroup[BGMsg, DummyBG](
        queue=queue, game_id=game_id, msg_type=BGMsg, bg_type=DummyBG
    )

    bg_tmp: list[DummyBG] = []
    for user_id in users:
        await bg_group.add(user_id=user_id, ws=AsyncMock())
        bg_tmp.append(bg_group._bg_bucket[user_id])

    await sleep(0.01)

    await bg_group.stop(ping)

    for bg in bg_tmp:
        assert len(bg.send_history) == 2

    for user_id in users:
        assert bg_group._healthcheck_bucket.get(user_id) is None
        assert bg_group._bg_bucket.get(user_id) is None


@pytest.mark.asyncio
async def test_bg():
    class DummyBG[T: BGMsg](BG[T]):
        send_history: list[T] = []
        recv_history: list[T] = []

        async def _send(self, msg: T):
            self.send_history.append(msg)

        async def _recv(self, msg: T):
            self.recv_history.append(msg)

    ws = AsyncMock()
    ping = BGMsg(event=BGMsgEvent.PING)
    pong = BGMsg(event=BGMsgEvent.PONG)
    ws.receive_bytes = AsyncMock(side_effect=[pong.model_dump_json().encode()])
    bg = DummyBG[BGMsg](ws=ws, msg_type=BGMsg)

    await bg.start(ping)
    await bg.ping()
    await bg.put_msg(ping)

    await sleep(0.01)

    await bg.stop(ping)

    assert len(bg.send_history) == 4
    assert len(bg.recv_history) == 1
