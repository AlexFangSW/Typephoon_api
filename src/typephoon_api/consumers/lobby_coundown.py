from .base import AbstractConsumer


class LobbyCountdownConsumer(AbstractConsumer):

    async def prepare(self):
        self._service = ""
        ...

    async def start(self):
        ...

    async def stop(self):
        ...
