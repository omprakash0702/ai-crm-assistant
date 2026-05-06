import os
import json
import redis
from dotenv import load_dotenv

load_dotenv()

USE_CACHE = True

_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)

_HIT_KEY    = "sys:cache_hits"
_MISS_KEY   = "sys:cache_misses"
_RETRY_KEY  = "sys:retry_count"
_FAILED_KEY = "sys:failed_requests"


def get_cache(key: str):
    try:
        value = _client.get(key)
        if value is None:
            try:
                _client.incr(_MISS_KEY)
            except Exception:
                pass
            return None
        try:
            _client.incr(_HIT_KEY)
        except Exception:
            pass
        return json.loads(value)
    except Exception:
        return None


def incr_retry():
    try:
        _client.incr(_RETRY_KEY)
    except Exception:
        pass


def incr_failed_request():
    try:
        _client.incr(_FAILED_KEY)
    except Exception:
        pass


def get_resilience_stats() -> dict:
    try:
        retries = int(_client.get(_RETRY_KEY)  or 0)
        failed  = int(_client.get(_FAILED_KEY) or 0)
        return {"retry_count": retries, "failed_requests": failed}
    except Exception:
        return {"retry_count": 0, "failed_requests": 0}


def set_cache(key: str, value, ttl: int = 300):
    try:
        _client.setex(key, ttl, json.dumps(value))
    except Exception:
        pass


def get_cache_stats() -> dict:
    try:
        hits   = int(_client.get(_HIT_KEY)  or 0)
        misses = int(_client.get(_MISS_KEY) or 0)
        total  = hits + misses
        hit_rate = round((hits / total) * 100, 1) if total > 0 else 0.0
        # Each cache hit avoids an LLM call (~1500 ms); gain = hit_rate% of that
        speed_gain_ms = round(hit_rate / 100 * 1500)
        return {
            "hits": hits,
            "misses": misses,
            "cache_hit_rate_percentage": hit_rate,
            "estimated_speed_gain_ms": speed_gain_ms,
        }
    except Exception:
        return {"hits": 0, "misses": 0, "cache_hit_rate_percentage": 0.0, "estimated_speed_gain_ms": 0}
