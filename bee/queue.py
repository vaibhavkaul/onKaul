"""Redis queue helpers for worker bees."""

from redis import Redis
from rq import Queue

from config import config


def get_redis_connection() -> Redis:
    """Return a Redis connection using config.REDIS_URL."""
    return Redis.from_url(config.REDIS_URL)


def get_queue() -> Queue:
    """Return the default RQ queue."""
    return Queue(name=config.REDIS_QUEUE_NAME, connection=get_redis_connection())
