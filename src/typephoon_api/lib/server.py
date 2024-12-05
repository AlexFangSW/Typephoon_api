from contextlib import asynccontextmanager
from logging import getLogger
from fastapi import FastAPI

from ..types.setting import Setting

logger = getLogger(__name__)


class TypephoonServer(FastAPI):

    def __init__(self, settings: Setting, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setting = settings

    async def prepare(self):
        ...

    async def cleanup(self):
        ...


@asynccontextmanager
async def lifespan(app: TypephoonServer):
    logger.info("lifespan startup")
    await app.prepare()

    yield

    logger.info("lifespan shutdown")
    await app.cleanup()


async def create_server() -> TypephoonServer:
    ...
