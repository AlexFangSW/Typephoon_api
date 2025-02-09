from logging import getLogger
from aio_pika import Message
from aio_pika.abc import AbstractExchange, DeliveryMode
from pamqp.commands import Basic
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .lobby import LobbyBGMsgEvent
from ...types.amqp import LobbyNotifyMsg
from ...repositories.game import GameRepo
from ...repositories.lobby_cache import LobbyCacheRepo
from ...types.errors import PublishNotAcknowledged

logger = getLogger(__name__)


async def remove_user_from_lobby(
    game_id: int,
    user_id: str,
    exchange: AbstractExchange,
    lobby_cache_repo: LobbyCacheRepo,
    sessionmaker: async_sessionmaker[AsyncSession],
):
    """
    Remove callback for lobby background
    """

    logger.debug("remove user !!!!, game_id: %s, user_id: %s", game_id, user_id)

    async with lobby_cache_repo.lock(game_id):
        did_delete = await lobby_cache_repo.remove_player(
            game_id=game_id, user_id=user_id
        )

    if did_delete:
        logger.debug("deleted player from cache, decrease player count")
        async with sessionmaker() as session:
            repo = GameRepo(session)
            game = await repo.decrease_player_count(game_id)
            if not game:
                logger.warning("game not found, game_id: %s", game_id)
            await session.commit()

    # notify all servers
    msg = (
        LobbyNotifyMsg(
            notify_type=LobbyBGMsgEvent.USER_LEFT, game_id=game_id, user_id=user_id
        )
        .model_dump_json()
        .encode()
    )
    amqp_msg = Message(msg, delivery_mode=DeliveryMode.PERSISTENT)
    confirm = await exchange.publish(message=amqp_msg, routing_key="")
    if not isinstance(confirm, Basic.Ack):
        raise PublishNotAcknowledged("publish user left message failed")
