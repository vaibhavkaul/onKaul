"""RQ worker entrypoint for bee tasks."""

import os
import sys

from rq import SimpleWorker, Worker

from bee.queue import get_redis_connection
from config import config


def main():
    """Start an RQ worker for the configured queue."""
    redis_conn = get_redis_connection()
    use_simple = os.getenv("RQ_SIMPLE_WORKER", "").lower() in {"1", "true", "yes"} or sys.platform == "darwin"
    worker_cls = SimpleWorker if use_simple else Worker
    worker = worker_cls([config.REDIS_QUEUE_NAME], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
