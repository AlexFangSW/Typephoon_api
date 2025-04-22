from abc import ABC, abstractmethod

from aio_pika.abc import AbstractRobustConnection

from ..types.setting import Setting


class AbstractConsumer(ABC):
    def __init__(self, setting: Setting, amqp_conn: AbstractRobustConnection) -> None:
        self._setting = setting
        self._amqp_conn = amqp_conn

    @abstractmethod
    async def prepare(self):
        raise NotImplementedError()

    @abstractmethod
    async def start(self):
        raise NotImplementedError()

    @abstractmethod
    async def stop(self):
        raise NotImplementedError()
