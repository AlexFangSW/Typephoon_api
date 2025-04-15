from os import getenv

AMQP_HOST = getenv("AMQP_HOST")
PG_HOST = getenv("PG_HOST")
REDIS_HOST = getenv("REDIS_HOST")
SERVER_NAME = getenv("SERVER_NAME", None)
