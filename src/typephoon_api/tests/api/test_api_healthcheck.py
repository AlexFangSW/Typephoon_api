import pytest
from httpx import AsyncClient

from ...types.responses.base import SuccessResponse
from ..helper import *


@pytest.mark.asyncio
async def test_api_healthcheck(client: AsyncClient):
    ret = await client.get("/healthcheck/alive")
    ret.raise_for_status()
    assert ret.json() == SuccessResponse().model_dump()

    ret = await client.get("/healthcheck/ready")
    ret.raise_for_status()
    assert ret.json() == SuccessResponse().model_dump()
