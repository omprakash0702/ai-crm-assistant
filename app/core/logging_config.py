import json
import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_logger = logging.getLogger(__name__)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":     record.levelname,
            "event":     record.getMessage(),
        }
        for key in (
            "user_id", "model", "latency_ms", "llm_time_ms",
            "cost_usd", "tokens_used", "route",
            "method", "path", "status_code",
        ):
            val = getattr(record, key, None)
            if val is not None:
                data[key] = val
        if record.exc_info:
            data["logger"] = record.name
            data["error"]  = self.formatException(record.exc_info)
        return json.dumps(data)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        t = time.time()
        response = await call_next(request)
        latency_ms = round((time.time() - t) * 1000, 2)
        user = getattr(request.state, "user", None)
        _logger.info(
            "api_request",
            extra={
                "method":      request.method,
                "path":        request.url.path,
                "status_code": response.status_code,
                "user_id":     user["id"] if user else None,
                "latency_ms":  latency_ms,
            },
        )
        return response


def setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]
