import os
from redis import Redis
from rq import Queue
from rq.job import Job
from dotenv import load_dotenv

load_dotenv()

# RQ requires decode_responses=False — it stores pickled binary, not strings.
# This is intentionally separate from the cache client in redis_client.py.
_redis_conn = Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

_queue = Queue(connection=_redis_conn)


def _run_summarize(text: str) -> str:
    from app.ai.tools import summarize_text
    return summarize_text.invoke(text)


def enqueue_summarize(text: str) -> str:
    job = _queue.enqueue(_run_summarize, text)
    _redis_conn.incr('rq:total_enqueued')
    return job.id


def get_queue_metrics() -> dict:
    pending = len(_queue)
    raw = _redis_conn.get('rq:total_enqueued')
    total = int(raw) if raw else 0
    return {"pending_jobs": pending, "total_jobs_processed": total}


def get_job_result(job_id: str) -> dict:
    try:
        job = Job.fetch(job_id, connection=_redis_conn)
        return {
            "id": job.id,
            "status": job.get_status(),
            "result": job.result,
        }
    except Exception as e:
        return {"error": str(e)}
