from redis import Redis
from rq import Worker

from app.core.config import get_settings


def run_worker():
    settings = get_settings()
    redis_conn = Redis.from_url(settings.redis_url)
    worker = Worker(['sweep'], connection=redis_conn)
    worker.work(with_scheduler=True)


if __name__ == '__main__':
    run_worker()
