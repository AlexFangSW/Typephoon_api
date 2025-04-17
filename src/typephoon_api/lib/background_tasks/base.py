"""
Background tasks for websockets.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from asyncio import (
    CancelledError,
    Event,
    Queue,
    Task,
    create_task,
)
from collections import defaultdict
from enum import StrEnum
from logging import getLogger
from typing import Type

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from pydantic import BaseModel

logger = getLogger(__name__)


class BGManager[MT: BGMsg, BT: BG]:
    """
    Background manager

    Attributes:
    - _pool: {game_id: dict[user_id, BG], ...}
    """

    def __init__(self) -> None:
        self._pool: defaultdict[int, dict[str, BT]] = defaultdict(dict)

    async def add(self, game_id: int, bg: BT, init_msg: MT | None = None):
        logger.debug("game_id: %s", game_id)
        await bg.start(init_msg)
        self._pool[game_id][bg.user_id] = bg

    async def remove_user(
        self, game_id: int, user_id: str, final_msg: MT | None = None
    ):
        logger.debug(
            "game_id: %s, user_id: %s, final_msg: %s", game_id, user_id, final_msg
        )

        if game_id not in self._pool:
            return

        if user_id not in self._pool[game_id]:
            return

        await self._pool[game_id][user_id].stop(final_msg)
        self._pool[game_id].pop(user_id)

        # remove games with zero connections
        if self._pool[game_id] == {}:
            self._pool.pop(game_id)

    async def remove_game(self, game_id: int, final_msg: MT | None = None):
        logger.debug("game_id: %s, final_msg: %s", game_id, final_msg)
        if game_id not in self._pool:
            return

        stop_tasks: list[Task] = []
        for user_id, bg in self._pool[game_id].items():
            stop_tasks.append(
                create_task(bg.stop(final_msg), name=f"{game_id}-{user_id}-remove-task")
            )

        await asyncio.gather(*stop_tasks)
        self._pool.pop(game_id, None)

    async def cleanup(self, final_msg: MT | None = None):
        logger.debug("cleanup, %s games", len(self._pool.keys()))

        stop_tasks: list[Task] = []
        for game_id in list(self._pool.keys()):
            for user_id, bg in self._pool[game_id].items():
                stop_tasks.append(
                    create_task(
                        bg.stop(final_msg), name=f"{game_id}-{user_id}-remove-task"
                    )
                )

        await asyncio.gather(*stop_tasks)

    async def broadcast(self, game_id: int, msg: MT):
        logger.debug("game_id: %s, msg: %s", game_id, msg)
        if game_id not in self._pool:
            return

        for _, bg in self._pool[game_id].items():
            await bg.put_msg(msg)


class BGMsgEvent(StrEnum):
    """
    all message event enums must have this attributes
    """

    PING = "PING"
    PONG = "PONG"


class BGMsg[T](BaseModel):
    event: T
    game_id: int

    def slim_dump_json(self) -> str:
        return self.model_dump_json(exclude_none=True)


class BG[T: BGMsg](ABC):
    """
    background instance
    """

    def __init__(
        self, ws: WebSocket, msg_type: Type[T], user_id: str, game_id: int
    ) -> None:
        self._ws = ws
        self._queue: Queue[T] = Queue()
        self._msg_type = msg_type
        self._user_id = user_id
        self._game_id = game_id
        self.closed = Event()

    async def close_wait(self):
        return await self.closed.wait()

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def game_id(self) -> int:
        return self._game_id

    @property
    def _name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def _send(self, msg: T):
        """
        send logic
        """
        raise NotImplementedError()

    async def _send_loop(self):
        logger.debug("_send_loop start")
        try:
            while True:
                msg = await self._queue.get()
                await self._send(msg)
        except CancelledError:
            logger.debug(
                "%s, send loop closed user_id: %s, game_id: %s",
                self._name,
                self._user_id,
                self._game_id,
            )
        except:
            logger.exception(
                "%s, send loop error, user_id: %s, game_id: %s",
                self._name,
                self._user_id,
                self._game_id,
            )
        finally:
            await self.stop()

    @abstractmethod
    async def _recv(self, msg: T):
        """
        receive logic
        """
        raise NotImplementedError()

    async def _recv_loop(self):
        logger.debug("_recv_loop start")
        try:
            while True:
                msg = await self._ws.receive_text()
                msg = self._msg_type.model_validate_json(msg)
                await self._recv(msg)
        except WebSocketDisconnect:
            logger.debug(
                "%s, recv loop closed user_id: %s, game_id: %s",
                self._name,
                self._user_id,
                self._game_id,
            )
        except:
            logger.exception(
                "%s, recv loop error, user_id: %s, game_id: %s",
                self._name,
                self._user_id,
                self._game_id,
            )
        finally:
            await self.stop()

    async def put_msg(self, msg: T):
        """
        put message to be sent through websocket
        """
        await self._queue.put(msg)

    async def start(self, init_msg: T | None = None):
        logger.debug("start")
        if init_msg:
            await self._send(init_msg)
        self._send_task = create_task(
            self._send_loop(), name=f"{self._name}-send-loop-{self._user_id}"
        )
        self._recv_task = create_task(
            self._recv_loop(), name=f"{self._name}-recv-loop-{self._user_id}"
        )

    async def stop(self, final_msg: T | None = None):
        logger.debug("stop")
        self._send_task.cancel()
        self._recv_task.cancel()
        try:
            if final_msg:
                await self._send(final_msg)
            if self._ws.client_state != WebSocketState.DISCONNECTED:
                await self._ws.close()
        except Exception as ex:
            logger.warning("stop error: %s", str(ex))
        finally:
            self.closed.set()
