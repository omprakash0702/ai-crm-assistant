import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.ai.client import llm as groq_llm, SYSTEM_PROMPT
from app.core.context import current_user_id
from app.core.redis_client import incr_retry, incr_failed_request
from app.db.connection import get_connection, release_connection

load_dotenv()

logger = logging.getLogger(__name__)

_REASONING_TASKS = {"suggest"}
_MAX_RETRIES  = 3
_TIMEOUT_SECS = 5
_FALLBACK_MSG = "I'm unable to process your request right now. Please try again."

_executor = ThreadPoolExecutor(max_workers=4)

_openai_llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=os.getenv("OPENAI_API_KEY"),
)

# Cost per token (USD)
_RATES = {
    "groq":   {"input": 0.05  / 1_000_000, "output": 0.08  / 1_000_000},
    "openai": {"input": 0.150 / 1_000_000, "output": 0.600 / 1_000_000},
}

last_llm_time_ms: float = 0.0


def route_model(task_type: str) -> str:
    return "openai" if task_type in _REASONING_TASKS else "groq"


def _log_cost(model_name: str, response, messages, latency_ms: float):
    input_tokens = output_tokens = None

    # Try usage_metadata (newer LangChain)
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens  = response.usage_metadata.get("input_tokens")
        output_tokens = response.usage_metadata.get("output_tokens")

    # Try response_metadata (older LangChain / Groq)
    if input_tokens is None and hasattr(response, "response_metadata"):
        usage = response.response_metadata.get("token_usage", {})
        input_tokens  = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")

    # Fallback: estimate from text length (~4 chars per token)
    if input_tokens is None:
        input_tokens = sum(len(m.content) for m in messages) // 4
    if output_tokens is None:
        output_tokens = len(response.content) // 4

    rates = _RATES.get(model_name, _RATES["groq"])
    cost  = round(input_tokens * rates["input"] + output_tokens * rates["output"], 8)

    logger.info(
        "llm_call",
        extra={
            "model":        model_name,
            "user_id":      current_user_id.get(),
            "latency_ms":   latency_ms,
            "tokens_used":  input_tokens + output_tokens,
            "cost_usd":     cost,
        },
    )
    _persist_llm_call(model_name, latency_ms, cost, input_tokens + output_tokens)


def _persist_llm_call(model_name: str, latency_ms: float, cost_usd: float, tokens_used: int):
    uid = current_user_id.get()
    if uid is None:
        return
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO llm_calls (user_id, model, latency_ms, cost_usd, tokens_used)"
            " VALUES (%s, %s, %s, %s, %s)",
            (uid, model_name, latency_ms, cost_usd, tokens_used),
        )
        conn.commit()
        cur.close()
    except Exception:
        logger.error("Failed to persist llm_call row", exc_info=True)
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        release_connection(conn)


def _invoke_with_retry(model, messages):
    last_exc = None
    for _ in range(_MAX_RETRIES):
        try:
            return _executor.submit(model.invoke, messages).result(timeout=_TIMEOUT_SECS)
        except Exception as e:
            last_exc = e
            incr_retry()
    raise last_exc


def _timed_invoke(model, messages) -> str:
    global last_llm_time_ms
    model_name = "openai" if model is _openai_llm else "groq"
    t = time.time()
    response = _invoke_with_retry(model, messages)
    last_llm_time_ms = round((time.time() - t) * 1000, 2)
    _log_cost(model_name, response, messages, last_llm_time_ms)
    return response.content


def invoke_routed(prompt: str, task_type: str) -> str:
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
    primary = route_model(task_type)

    if primary == "openai":
        try:
            return _timed_invoke(_openai_llm, messages)
        except Exception:
            pass
        try:
            return _timed_invoke(groq_llm, messages)
        except Exception:
            incr_failed_request()
            return _FALLBACK_MSG

    try:
        return _timed_invoke(groq_llm, messages)
    except Exception:
        pass
    try:
        return _timed_invoke(_openai_llm, messages)
    except Exception:
        incr_failed_request()
        return _FALLBACK_MSG
