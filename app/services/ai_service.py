import logging
import re
import time
from app.ai.router import run, _route
from app.ai.model_router import invoke_routed, route_model
from app.core.context import current_user_id
import app.ai.model_router as _router_module

logger = logging.getLogger(__name__)


def format_notes_batch(notes: list[str], types: list[str] | None = None) -> list[str | None]:
    """Format raw CRM notes into formal sentences, consistent with each interaction type."""
    non_empty = [(i, n) for i, n in enumerate(notes) if n and n.strip()]
    if not non_empty:
        return [None] * len(notes)

    def _type_label(i: int) -> str:
        if types and i < len(types) and types[i]:
            return types[i]
        return "Interaction"

    lines_in = "\n".join(
        f"[{_type_label(i)}] {n}" for i, n in non_empty
    )
    prompt = (
        f"Rewrite each CRM note below into one formal sentence.\n"
        f"Each note is prefixed with its interaction type in brackets — use that type consistently.\n"
        f"Keep all facts from the original. Do not invent new details.\n"
        f"If a note is too vague to understand, write exactly: —\n"
        f"Return exactly {len(non_empty)} lines — one per note, same order.\n"
        f"Do not include the bracket prefix, numbers, or bullets in your output.\n\n"
        f"{lines_in}"
    )
    try:
        result = invoke_routed(prompt, "summarize")
        raw_lines = [l.strip() for l in result.strip().splitlines() if l.strip()]
        raw_lines = [re.sub(r"^\d+[\.\)]\s*", "", l) for l in raw_lines]

        output: list[str | None] = [None] * len(notes)
        for j, (i, _) in enumerate(non_empty):
            if j < len(raw_lines):
                val = raw_lines[j]
                output[i] = None if val == "—" else val
        return output
    except Exception:
        return [None] * len(notes)


def chat(user_input: str, user_id: int, history=None) -> str:
    token = current_user_id.set(user_id)
    try:
        task_type  = _route(user_input)
        model_name = route_model(task_type)

        t = time.time()
        result = run(user_input, history=history)
        total_ms = round((time.time() - t) * 1000, 2)

        logger.info(
            "chat_request",
            extra={
                "user_id":     user_id,
                "route":       task_type,
                "model":       model_name,
                "latency_ms":  total_ms,
                "llm_time_ms": _router_module.last_llm_time_ms,
            },
        )
        return result
    finally:
        current_user_id.reset(token)
