import logging
from app.db.connection import get_connection, release_connection
from app.core.redis_client import get_cache_stats, get_resilience_stats

logger = logging.getLogger(__name__)


def get_system_metrics(user_id: int) -> dict:
    result = {
        "total_llm_calls": 0,
        "avg_latency_ms": 0.0,
        "total_cost_usd": 0.0,
        "model_usage": {"groq": 0, "openai": 0},
        "cache_hits": 0,
        "cache_misses": 0,
    }

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                COUNT(*)::int,
                ROUND(AVG(latency_ms)::numeric, 2)::float,
                ROUND(SUM(cost_usd)::numeric, 6)::float,
                COUNT(*) FILTER (WHERE model = 'groq')::int,
                COUNT(*) FILTER (WHERE model = 'openai')::int
            FROM llm_calls
            WHERE user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
        cur.close()
        if row and row[0]:
            result["total_llm_calls"] = row[0]
            result["avg_latency_ms"] = float(row[1] or 0)
            result["total_cost_usd"] = float(row[2] or 0)
            result["model_usage"]["groq"] = row[3]
            result["model_usage"]["openai"] = row[4]
    except Exception:
        logger.error("get_system_metrics DB query failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)

    stats = get_cache_stats()
    result["cache_hits"] = stats["hits"]
    result["cache_misses"] = stats["misses"]
    result["cache_hit_rate_percentage"] = stats["cache_hit_rate_percentage"]
    result["estimated_speed_gain_ms"] = stats["estimated_speed_gain_ms"]

    resilience = get_resilience_stats()
    result["retry_count"] = resilience["retry_count"]
    result["failed_requests"] = resilience["failed_requests"]

    return result
