import os
from redis import Redis
from rq import SimpleWorker, Queue
from dotenv import load_dotenv

load_dotenv()

redis_conn = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

if __name__ == "__main__":
    worker = SimpleWorker(queues=[Queue(connection=redis_conn)], connection=redis_conn)
    worker.work()
