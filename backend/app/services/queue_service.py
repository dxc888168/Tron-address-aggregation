from redis import Redis
from rq import Queue

from app.core.config import get_settings


_queue = None


def get_queue() -> Queue:
    global _queue
    if _queue is None:
        settings = get_settings()
        redis_conn = Redis.from_url(settings.redis_url)
        _queue = Queue('sweep', connection=redis_conn)
    return _queue
