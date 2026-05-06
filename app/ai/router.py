import re
from app.ai.tools import log_interaction, edit_interaction, summarize_text, extract_entities, suggest_next_action
from app.utils.text import extract_name_simple, formal_doctor_name

_EDIT_WORDS      = ("update", "edit", "change", "correct", "fix", "modify")
_SUMMARIZE_WORDS = ("summarize", "summary", "shorten", "condense", "brief", "all interaction")
_EXTRACT_WORDS   = ("extract", "pull out", "identify", "list the", "what doctor",
                    "which medicine", "what product")
_SUGGEST_WORDS   = ("next step", "what should i do", "suggest", "recommend",
                    "follow up", "follow-up", "what now", "advice", "plan",
                    "what next", "what to do", "should i do")
_PRONOUNS        = ("him", "her", "them", "his", "her", "their", "this doctor",
                    "that doctor", "the doctor")
_CONFIRMATION_WORDS = {"yes", "yeah", "y", "confirm", "ok", "okay", "sure", "yep"}


def _last_doctor_in_history(history) -> str | None:
    """Scan history newest-first for any doctor name mentioned by user or agent."""
    if not history:
        return None
    for msg in reversed(history):
        text = msg.text if hasattr(msg, 'text') else msg.get('text', '')
        # Check agent responses: "logged for Dr. X", "interactions with Dr. X"
        m = re.search(r'(?:for|with|about)\s+(Dr\.?\s+[A-Za-z]+)', text, re.IGNORECASE)
        if m:
            return formal_doctor_name(m.group(1))
        # Check plain "Dr. X" pattern
        found = extract_name_simple(text)
        if found:
            return found
    return None


def _inject_context(text: str, history) -> str:
    """Append the last known doctor from history when the message names none."""
    has_doctor = bool(extract_name_simple(text)) or bool(
        re.search(r'\bdr\.?\s+\w+', text, re.IGNORECASE)
    )
    if has_doctor:
        return text
    last = _last_doctor_in_history(history)
    if last:
        return f"{text} (about {last})"
    return text


def _route(text: str) -> str:
    lower = text.lower()
    # Context-setting messages like "regarding Dr X" with no action → suggest
    if re.match(r'^(regarding|about)\s+dr\.?\s+', lower):
        return "suggest"
    if any(w in lower for w in _EDIT_WORDS) and re.search(r"\b\d+\b", lower):
        return "edit"
    if any(w in lower for w in _SUMMARIZE_WORDS):
        return "summarize"
    if any(w in lower for w in _EXTRACT_WORDS):
        return "extract"
    if any(w in lower for w in _SUGGEST_WORDS):
        return "suggest"
    return "log"


def run(user_input: str, history=None) -> str:
    if user_input.strip().lower() in _CONFIRMATION_WORDS:
        return (
            "To create a new entry, please resend your original message with the prefix:\n"
            "new entry: <your message>\n\n"
            "Example: new entry: Met Dr. Patel, discussed Metformin"
        )

    route = _route(user_input)

    # Inject history context only for routes that look up a doctor — never for log/edit
    # (injecting on log would stamp the wrong doctor on a brand-new entry)
    if route in ("suggest", "summarize", "extract"):
        enriched = _inject_context(user_input, history)
    else:
        enriched = user_input

    if route == "edit":
        return edit_interaction.invoke(enriched)
    if route == "summarize":
        return summarize_text.invoke(enriched)
    if route == "extract":
        return extract_entities.invoke(enriched)
    if route == "suggest":
        return suggest_next_action.invoke(enriched)
    return log_interaction.invoke(enriched)
