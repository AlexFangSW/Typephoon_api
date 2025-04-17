from unittest.mock import AsyncMock

from aio_pika import Message
from pamqp.commands import Basic

from ...lib.background_tasks.game import GameBG, GameBGMsg, GameBGMsgEvent
from ...types.amqp import KeystrokeHeader, KeystrokeMsg
from ..helper import *


@pytest.mark.asyncio
async def test_game_bg_send(setting: Setting):
    ws = AsyncMock()
    ws.send_bytes = AsyncMock()
    user_id = "123"
    exchange = AsyncMock()
    game_id = 123
    bg = GameBG(
        ws=ws, user_id=user_id, exchange=exchange, setting=setting, game_id=game_id
    )
    await bg.start()

    msg = GameBGMsg(
        event=GameBGMsgEvent.KEY_STOKE,
        user_id="222",
        word_index=20,
        char_index=4,
        game_id=game_id,
    )
    await bg._send(msg)

    assert ws.send_text.called
    assert ws.send_text.call_args.args == (msg.model_dump_json(),)

    await bg.stop()


@pytest.mark.asyncio
async def test_game_bg_recv(setting: Setting):
    ws = AsyncMock()
    user_id = "123"
    exchange = AsyncMock()
    exchange.publish = AsyncMock(return_value=Basic.Ack())
    game_id = 123
    server_name = "aaa"
    bg = GameBG(
        ws=ws,
        user_id=user_id,
        exchange=exchange,
        setting=setting,
        game_id=game_id,
        server_name=server_name,
    )
    await bg.start()

    word_index = 20
    char_index = 4
    inpt_msg = GameBGMsg(
        event=GameBGMsgEvent.KEY_STOKE,
        user_id=user_id,
        word_index=word_index,
        char_index=char_index,
        game_id=game_id,
    )
    answer = KeystrokeMsg(
        game_id=game_id, user_id=user_id, word_index=word_index, char_index=char_index
    )
    await bg._recv(inpt_msg)

    assert exchange.publish.called
    amqp_msg: Message = exchange.publish.call_args.kwargs["message"]
    assert amqp_msg.body == answer.model_dump_json().encode()
    assert KeystrokeHeader.model_validate(amqp_msg.headers).source == server_name

    await bg.stop()
