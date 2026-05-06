import logging
import time
from fastapi import Depends, HTTPException
from app.core.redis_client import _client as _redis
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

_LIMIT  = 60   # requests
_WINDOW = 60   # seconds


def rate_limit(user: dict = Depends(get_current_user)) -> dict:
    bucket = int(time.time() // _WINDOW)
    key    = f"rl:{user['id']}:{bucket}"
    try:
        count = _redis.incr(key)
        if count == 1:
            _redis.expire(key, _WINDOW)
        if count > _LIMIT:
            logger.info("rate_limit_exceeded", extra={"user_id": user["id"]})
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again in a minute.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.error("rate_limit check failed, allowing request", exc_info=True)
    return user
