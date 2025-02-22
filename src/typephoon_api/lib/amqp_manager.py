from dataclasses import dataclass
from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from .util import get_dict_hash

from ..types.setting import Setting


@dataclass(slots=True)
class UpdatedQueueNames:
    lobby_multi_wait: str
    game_cleanup_wait: str
    game_start_wait: str


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

        game_start_exchange = await channel.declare_exchange(
            name=self._setting.amqp.game_start_fanout_exchange,
            type=ExchangeType.FANOUT,
            durable=True,
        )

        game_keystroke_exchange = await channel.declare_exchange(
            name=self._setting.amqp.game_keystroke_fanout_exchange,
            type=ExchangeType.FANOUT,
            durable=True,
        )

        game_cleanup_exchange = await channel.declare_exchange(
            name=self._setting.amqp.game_cleanup_direct_exchange,
            type=ExchangeType.DIRECT,
            durable=True,
        )

        # queues
        game_cleanup_queue = await channel.declare_queue(
            name=self._setting.amqp.game_cleanup_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await game_cleanup_queue.bind(
            exchange=game_cleanup_exchange,
            routing_key=self._setting.amqp.game_cleanup_queue_routing_key,
        )

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

        game_start_queue = await channel.declare_queue(
            name=self._setting.amqp.game_start_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await game_start_queue.bind(exchange=game_start_exchange)

        lobby_countdown_queue = await channel.declare_queue(
            name=self._setting.amqp.lobby_countdown_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"},
        )
        await lobby_countdown_queue.bind(
            exchange=lobby_countdown_exchange,
            routing_key=self._setting.amqp.lobby_countdown_queue_routing_key,
        )

        # use default exchange to publish to this queue
        lobby_multi_countdown_wait_args = {
            "x-queue-type": "quorum",
            "x-message-ttl": self._setting.game.lobby_countdown * 1000,
            "x-dead-letter-exchange": lobby_countdown_exchange.name,
            "x-dead-letter-routing-key": self._setting.amqp.lobby_countdown_queue_routing_key,
        }
        lobby_multi_countdown_wait_name = f"{self._setting.amqp.lobby_multi_countdown_wait_queue}.{get_dict_hash(lobby_multi_countdown_wait_args)}"
        await channel.declare_queue(
            name=lobby_multi_countdown_wait_name,
            durable=True,
            arguments=lobby_multi_countdown_wait_args,
        )

        game_cleanup_wait_args = {
            "x-queue-type": "quorum",
            "x-message-ttl": self._setting.game.cleanup_countdown * 1000,
            "x-dead-letter-exchange": game_cleanup_exchange.name,
            "x-dead-letter-routing-key": self._setting.amqp.game_cleanup_queue_routing_key,
        }
        game_cleanup_wait_name = f"{self._setting.amqp.game_cleanup_wait_queue}.{get_dict_hash(game_cleanup_wait_args)}"
        await channel.declare_queue(
            name=game_cleanup_wait_name,
            durable=True,
            arguments=game_cleanup_wait_args,
        )

        game_start_wait_args = {
            "x-queue-type": "quorum",
            "x-message-ttl": self._setting.game.start_countdown * 1000,
            "x-dead-letter-exchange": game_start_exchange.name,
            "x-dead-letter-routing-key": self._setting.amqp.game_start_queue_routing_key,
        }
        game_start_wait_name = f"{self._setting.amqp.game_start_wait_queue}.{get_dict_hash(game_start_wait_args)}"
        await channel.declare_queue(
            name=game_start_wait_name,
            durable=True,
            arguments=game_start_wait_args,
        )

        await channel.close()

        return UpdatedQueueNames(
            lobby_multi_wait=lobby_multi_countdown_wait_name,
            game_cleanup_wait=game_cleanup_wait_name,
            game_start_wait=game_start_wait_name,
        )
