from .base import AbstractConsumer


class LobbyNotifyRandomConsumer(AbstractConsumer):
    """
    This consumer just consumes messages and pass them down.
    Logic should be in "LobbyBackground".
    """

    async def prepare(self):
        ...

    async def start(self):
        ...

    async def stop(self):
        ...
