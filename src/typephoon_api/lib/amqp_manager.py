from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from .util import get_dict_hash

from ..types.setting import Setting


class AMQPManager:

    def __init__(self, setting: Setting, amqp_conn: AbstractRobustConnection) -> None:
        self._setting = setting
        self._amqp_conn = amqp_conn

    async def setup(self):
        channel = await self._amqp_conn.channel()

        # exchanges
        lobby_countdown_exchange = await channel.declare_exchange(
            name=self._setting.amqp.lobby_countdown_direct_exchange,
            type=ExchangeType.DIRECT,
            durable=True,
        )

        lobby_notify_exchange = await channel.declare_exchange(
            name=self._setting.amqp.lobby_notify_fanout_exchange,
            type=ExchangeType.FANOUT,
            durable=True,
        )

        game_keystroke_exchange = await channel.declare_exchange(
            name=self._setting.amqp.game_keystroke_fanout_exchange,
            type=ExchangeType.FANOUT,
            durable=True,
        )

        # queues
        game_keystroke_queue = await channel.declare_queue(
            name=self._setting.amqp.game_keystroke_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await game_keystroke_queue.bind(exchange=game_keystroke_exchange)

        lobby_notify_queue = await channel.declare_queue(
            name=self._setting.amqp.lobby_notify_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await lobby_notify_queue.bind(exchange=lobby_notify_exchange)

        lobby_countdown_queue = await channel.declare_queue(
            name=self._setting.amqp.lobby_countdown_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await lobby_countdown_queue.bind(
            exchange=lobby_countdown_exchange, routing_key="countdown"
        )

        # use default exchange to publish to this queue
        lobby_multi_countdown_args = {
            "x-queue-type": "quorum",
            "x-message-ttl": self._setting.game.lobby_countdown * 1000,
            "x-dead-letter-exchange": lobby_countdown_exchange.name,
            "x-dead-letter-routing-key": "countdown",
        }
        await channel.declare_queue(
            name=f"{self._setting.amqp.lobby_multi_countdown_wait_queue}.{get_dict_hash(lobby_multi_countdown_args)}",
            durable=True,
            arguments=lobby_multi_countdown_args,
        )

        # TODO: uncomment this when we add TEAM mode
        # use default exchange to publish to this queue
        # NEED dead letter policy
        # - dead letter exchange: <countdown exchange name>
        # - dead leter routing key: 'countdown'
        # await channel.declare_queue(
        #     name=self._setting.amqp.lobby_team_countdown_wait_queue,
        #     durable=True,
        #     arguments={"x-queue-type": "quorum"},
        # )

        await channel.close()
