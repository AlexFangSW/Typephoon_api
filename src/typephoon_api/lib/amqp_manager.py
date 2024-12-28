from aio_pika import ExchangeType
from aio_pika.abc import AbstractRobustConnection

from ..types.setting import Setting


class AMQPManager:

    def __init__(self, setting: Setting,
                 amqp_conn: AbstractRobustConnection) -> None:
        self._setting = setting
        self._amqp_conn = amqp_conn

    async def setup(self):
        channel = await self._amqp_conn.channel()

        countdown_exchange = await channel.declare_exchange(
            name=self._setting.amqp.countdown_direct_exchange,
            type=ExchangeType.DIRECT,
            durable=True)

        notify_exchange = await channel.declare_exchange(
            name=self._setting.amqp.lobby_random_notify_fanout_exchange,
            type=ExchangeType.FANOUT,
            durable=True)

        # notify exchange is fanout, no need for routing key
        notify_queue = await channel.declare_queue(
            name=self._setting.amqp.lobby_random_notify_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"})
        await notify_queue.bind(exchange=notify_exchange)

        # NEED dead letter policy
        # - dead letter exchange: <countdown exchange name>
        # - dead leter routing key: 'countdown'
        countdown_queue = await channel.declare_queue(
            name=self._setting.amqp.lobby_random_countdown_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"})
        await countdown_queue.bind(exchange=countdown_exchange,
                                   routing_key="countdown")

        # use default exchange to publish to this queue
        await channel.declare_queue(
            name=self._setting.amqp.lobby_random_countdown_wait_queue,
            durable=True,
            arguments={"x-queue-type": "quorum"})

        await channel.close()
