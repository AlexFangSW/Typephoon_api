"""
Background tasks for websockets.
Automatically cleans up on websocket desconnect.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from asyncio import Queue, Task, create_task, sleep
from dataclasses import dataclass
from enum import IntEnum
from logging import getLogger
from typing import Type

from fastapi import WebSocket
from pydantic import BaseModel


logger = getLogger(__name__)


class _BGMsgEvent(IntEnum):
    UPDATE = 0
    HEALTHCHECK_FAIL = 1


@dataclass(slots=True, frozen=True)
class _BGMsg:
    game_id: int
    user_id: str
    event: _BGMsgEvent


@dataclass(slots=True)
class _GroupBucketItem[MT: BGMsg, BT: BG]:
    group: BGGroup[MT, BT]

    @property
    def connections(self)-> int:
        return len(self.group._bg_bucket)

class BGManager[MT: BGMsg, BT: BG]:
    """
    background manager
    """

    def __init__(self, msg_type: Type[MT], bg_type: Type[BT]) -> None:
        self._queue: Queue[_BGMsg] = Queue()
        self._group_bucket: dict[int, _GroupBucketItem[MT, BT]] = {}
        self._msg_type = msg_type
        self._bg_type = bg_type

    async def get(self, game_id: int) -> BGGroup:
        """
        act like defaultdict, either create or return existing instance
        """
        if bucket_item := self._group_bucket.get(game_id):
            logger.debug("found bg_group, game_id: %s", game_id)
            return bucket_item.group

        logger.debug("create bg_group, game_id: %s", game_id)
        self._group_bucket[game_id] = _GroupBucketItem(
            group=BGGroup[self._msg_type, self._bg_type](
                queue=self._queue,
                game_id=game_id,
                msg_type=self._msg_type,
                bg_type=self._bg_type,
            )
        )
        return self._group_bucket[game_id].group

    async def remove(self, game_id: int, final_msg: MT | None = None):
        if bucket_item := self._group_bucket.get(game_id):
            await bucket_item.group.stop(final_msg)
            self._group_bucket.pop(game_id)
            logger.debug(
                "bg_group removed, game_id: %s, final_msg: %s", game_id, final_msg
            )

    async def _manage_loop(self):
        logger.debug("_manage_loop started")
        while True:
            msg = await self._queue.get()
            logger.debug("got msg: %s", msg)

            if not (bucket_item := self._group_bucket.get(msg.game_id)):
                logger.debug("game not found, game_id: %s", msg.game_id)
                continue

            if msg.event == _BGMsgEvent.HEALTHCHECK_FAIL:
                await bucket_item.group.remove(msg.user_id)

            logger.debug(
                "game_id: %s, connections: %s",
                msg.game_id,
                bucket_item.connections,
            )

            if bucket_item.connections == 0:
                await self.remove(msg.game_id)

    @property
    def _name(self) -> str:
        return type(self).__name__

    async def start(self):
        logger.debug("start")
        self._listener_task = create_task(
            self._manage_loop(), name=f"{self._name}-manage-loop"
        )

    async def stop(self, final_msg: MT | None = None):
        logger.debug("stop")
        self._listener_task.cancel()
        for game_id in list(self._group_bucket.keys()):
            await self.remove(game_id=game_id, final_msg=final_msg)


class BGGroup[MT: BGMsg, BT: BG]:
    """
    background group
    """

    def __init__(
        self,
        queue: Queue[_BGMsg],
        game_id: int,
        msg_type: Type[MT],
        bg_type: Type[BT],
        ping_interval: float = 30,
    ) -> None:
        self._game_id = game_id
        self._queue = queue
        self._bg_bucket: dict[str, BT] = {}
        self._healthcheck_bucket: dict[str, Task] = {}
        self._ping_interval = ping_interval
        self._msg_type = msg_type
        self._bg_type = bg_type

    @property
    def _name(self) -> str:
        return type(self).__name__

    async def add(self, user_id: str, ws: WebSocket, init_msg: MT | None = None):
        logger.debug("add bg, user_id: %s, init_msg: %s", user_id, init_msg)
        bg = self._bg_type(ws=ws, msg_type=self._msg_type)
        await bg.start(init_msg)
        self._bg_bucket[user_id] = bg
        self._healthcheck_bucket[user_id] = create_task(
            self._healthcheck_loop(user_id), name=f"{self._name}-healthcheck-loop"
        )
        await self._queue.put(
            _BGMsg(game_id=self._game_id, user_id=user_id, event=_BGMsgEvent.UPDATE)
        )

    async def remove(self, user_id: str, final_msg: MT | None = None):
        if bg := self._bg_bucket.get(user_id):
            self._healthcheck_bucket[user_id].cancel()
            self._healthcheck_bucket.pop(user_id)
            await bg.stop(final_msg)
            self._bg_bucket.pop(user_id)
            await self._queue.put(
                _BGMsg(
                    game_id=self._game_id, user_id=user_id, event=_BGMsgEvent.UPDATE
                )
            )
            logger.debug("bg removed, user_id: %s, final_msg: %s", user_id, final_msg)

    async def broadcast(self, msg: MT):
        for user_id, bg in self._bg_bucket.items():
            logger.debug("put msg, user_id: %s, msg: %s", user_id, msg)
            await bg.put_msg(msg)

    async def stop(self, final_msg: MT | None = None):
        for user_id in list(self._bg_bucket.keys()):
            await self.remove(user_id=user_id, final_msg=final_msg)

    async def _healthcheck_loop(self, user_id: str):
        """
        checks connection for specified user.
        if the connection is broken, notify background manager for clean up.
        """
        if not (bg := self._bg_bucket.get(user_id)):
            logger.warning(
                "bg not found, did this loop start before adding bg to bucket ? user_id: %s"
            )
            return

        while True:
            try:
                await bg.ping()
            except Exception as ex:
                logger.debug("healthcheck failed, error: %s", str(ex))
                await self._queue.put(
                    _BGMsg(
                        game_id=self._game_id,
                        user_id=user_id,
                        event=_BGMsgEvent.HEALTHCHECK_FAIL,
                    )
                )
                break
            await sleep(self._ping_interval)


class BGMsgEvent(IntEnum):
    PING = 0
    PONG = 1


class BGMsg(BaseModel):
    event: BGMsgEvent


class BG[T: BGMsg](ABC):
    """
    background instance
    """

    def __init__(self, ws: WebSocket, msg_type: Type[T]) -> None:
        self._ws = ws
        self._queue: Queue[T] = Queue()
        self._msg_type = msg_type

    @property
    def _name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def _send(self, msg: T):
        """
        send logic
        """
        raise NotImplemented()

    async def _send_loop(self):
        logger.debug("_send_loop start")
        while True:
            msg = await self._queue.get()
            await self._send(msg)

    @abstractmethod
    async def _recv(self, msg: T):
        """
        receive logic
        """
        raise NotImplemented()

    async def _recv_loop(self):
        logger.debug("_recv_loop start")
        while True:
            raw_msg = await self._ws.receive_bytes()
            msg = self._msg_type.model_validate_json(raw_msg)
            await self._recv(msg)

    async def put_msg(self, msg: T):
        """
        put message to be sent through websocket
        """
        await self._queue.put(msg)

    async def start(self, init_msg: T | None = None):
        logger.debug("start")
        if init_msg:
            await self._send(init_msg)
        self._recv_task = create_task(self._recv_loop(), name=f"{self._name}-recv-loop")
        self._send_task = create_task(self._send_loop(), name=f"{self._name}-send-loop")

    async def stop(self, final_msg: T | None = None):
        logger.debug("stop")
        if final_msg:
            await self._send(final_msg)
        self._send_task.cancel()
        self._recv_task.cancel()

    async def ping(self):
        logger.debug("ping")
        await self._send(self._msg_type(event=BGMsgEvent.PING))
