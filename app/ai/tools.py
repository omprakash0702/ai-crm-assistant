import logging
import re
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from app.ai.client import llm
from app.ai.model_router import invoke_routed
from app.core.context import current_user_id

logger = logging.getLogger(__name__)
from app.db.connection import get_connection, release_connection
from app.db.queries import fetch_doctor_history, is_duplicate, get_or_create_doctor, update_doctor_stats
from app.utils.text import extract_name_simple, normalize_doctor_name, formal_doctor_name, detect_interaction_type
from app.core.redis_client import get_cache, set_cache, USE_CACHE
from app.ai.validators import (
    is_valid_name, is_valid_sentiment, is_valid_response,
    is_valid_extract_response, doctor_exists_in_db,
    parse_doctor_from_extract,
)


@tool
def log_interaction(text: str) -> str:
    """Log a new doctor interaction to the CRM. Use when the user describes a meeting, visit, or call with a doctor."""
    uid = current_user_id.get()

    force = bool(re.match(r"^new\s+entry\s*:", text, re.IGNORECASE))
    if force:
        text = re.sub(r"^new\s+entry\s*:\s*", "", text, flags=re.IGNORECASE).strip()

    if not force and is_duplicate(text, uid):
        return (
            "This interaction already appears to be logged. "
            "Do you want to create a new entry? "
            "If yes, resend your message starting with: new entry: ..."
        )

    prompt = (
        "Extract from this CRM note. Return exactly 5 lines, no extra text:\n"
        "Doctor: <Dr. LastName only — do NOT include words like 'meeting', 'visit', 'call'. If no name, write Unknown>\n"
        "Type: <Call if phoned/called/rang | Visit if visited/clinic/in-person | Meeting if met/discussed/presented>\n"
        "Sentiment: <Positive ONLY if clearly satisfied/agreed | Negative ONLY if clearly unhappy/refused | else Neutral>\n"
        "Follow-up: <one action, max 8 words, from the text only>\n"
        "Summary: <one sentence, facts from text only>\n\n"
        f"Text: {text}\n\n"
        "Use only facts from the text. Do not add anything."
    )
    result = invoke_routed(prompt, "log")

    doctor_name = "Unknown"
    interaction_type = None
    sentiment = "Neutral"
    follow_up = "Schedule a follow-up meeting."
    summary = text[:120]

    for line in result.splitlines():
        line = line.strip()
        if line.lower().startswith("doctor:"):
            name = line.split(":", 1)[1].strip()
            if name.lower() not in ("unknown", "none", "n/a"):
                doctor_name = formal_doctor_name(name)
        elif line.lower().startswith("type:"):
            val = line.split(":", 1)[1].strip()
            if val in ("Call", "Visit", "Meeting"):
                interaction_type = val
        elif line.lower().startswith("sentiment:"):
            val = line.split(":", 1)[1].strip()
            if val in ("Positive", "Negative", "Neutral"):
                sentiment = val
        elif line.lower().startswith("follow-up:") or line.lower().startswith("follow up:"):
            follow_up = line.split(":", 1)[1].strip()
        elif line.lower().startswith("summary:"):
            summary = line.split(":", 1)[1].strip()

    # Keyword-based fallback if LLM didn't return a valid type
    if interaction_type is None:
        interaction_type = detect_interaction_type(text)

    if doctor_name == "Unknown":
        regex_name = extract_name_simple(text)
        if regex_name:
            doctor_name = formal_doctor_name(regex_name)

    if not is_valid_name(doctor_name):
        return "Could not identify a valid doctor name. Please include the doctor's name and try again."
    if not is_valid_sentiment(sentiment):
        return "Could not determine a valid sentiment from the input. Please rephrase and try again."

    try:
        doctor_id = get_or_create_doctor(normalize_doctor_name(doctor_name), uid)
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO interactions (doctor_name, interaction_type, notes, doctor_id, user_id)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (doctor_name, interaction_type, text, doctor_id, uid),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        release_connection(conn)
        update_doctor_stats(doctor_id)
        return (
            f"Interaction #{new_id} logged for {doctor_name}. "
            f"{summary} "
            f"Sentiment: {sentiment}. Follow-up: {follow_up}"
        )
    except Exception:
        logger.error("log_interaction DB write failed", exc_info=True)
        return "Something went wrong, please try again."


@tool
def edit_interaction(text: str) -> str:
    """Edit the notes of an existing interaction. Requires a numeric interaction ID in the text."""
    uid = current_user_id.get()

    match = re.search(r"\b(\d+)\b", text)
    if not match:
        return "Invalid interaction ID."
    record_id = int(match.group(1))
    notes = text[match.end():].strip().lstrip(",:- ")
    for prefix in ("with notes about ", "with notes ", "notes: ", "notes "):
        if notes.lower().startswith(prefix):
            notes = notes[len(prefix):]
            break
    if not notes:
        notes = text
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT doctor_name FROM interactions WHERE id = %s AND user_id = %s",
            (record_id, uid),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            release_connection(conn)
            return "Invalid interaction ID."
        doctor_name = row[0]
        cur.execute(
            "UPDATE interactions SET notes = %s WHERE id = %s AND user_id = %s",
            (notes, record_id, uid),
        )
        conn.commit()
        cur.close()
        release_connection(conn)
        return f"Interaction #{record_id} for {doctor_name} updated — notes: {notes}"
    except Exception:
        logger.error("edit_interaction DB write failed", exc_info=True)
        return "Something went wrong, please try again."


@tool
def summarize_text(text: str) -> str:
    """Summarize interaction notes. Fetches real notes from DB if a doctor name is mentioned."""
    uid = current_user_id.get()
    cache_key = f"summarize:{uid}:{text.strip().lower()}"

    if USE_CACHE:
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

    doctor_name = extract_name_simple(text)
    history = fetch_doctor_history(doctor_name, uid) if (doctor_name and uid) else []

    if doctor_name and uid and not history:
        return f"Sorry, but there is no entry for {doctor_name} in the CRM."

    if history:
        notes_text = "\n".join(f"- {r['notes']}" for r in history if r["notes"])
        prompt = (
            f"Summarize the logged interactions with {doctor_name} based on these notes:\n\n"
            f"{notes_text}\n\n"
            f"Write 1–2 sentences. Use only the facts above. Stop after the facts."
        )
    else:
        prompt = (
            f"The following is a note from a pharmaceutical sales rep:\n\n\"{text}\"\n\n"
            f"Write a 1–2 sentence summary of exactly what is stated above.\n"
            f"Use only what is written. Stop after the facts."
        )

    result = invoke_routed(prompt, "summarize")

    if not is_valid_response(result):
        return "Could not generate a summary. Please try again."

    if USE_CACHE:
        set_cache(cache_key, result)

    return result


@tool
def extract_entities(text: str) -> str:
    """Extract doctor name, product, location, and date. Enriches with DB history if doctor is already logged."""
    uid = current_user_id.get()
    doctor_name = extract_name_simple(text)
    history = fetch_doctor_history(doctor_name, uid) if (doctor_name and uid) else []

    db_context = ""
    if doctor_name and uid and not history:
        db_context = f"\n\nNote: {doctor_name} has no logged interactions in the CRM."
    elif history:
        db_context = (
            f"\n\nThis doctor has {len(history)} logged interaction(s) in the CRM. "
            f"Most recent note: \"{history[0]['notes']}\""
        )

    prompt = (
        "Extract only what is explicitly stated in the text below. "
        "Return exactly 4 lines, no other text:\n"
        "Doctor: [name or —]\n"
        "Product: [name or —]\n"
        "Location: [name or —]\n"
        "Date: [date or —]\n\n"
        f"Text: {text}{db_context}\n\n"
        "For any missing field write exactly: —\n"
        "Do not add sentences, summaries, or anything not directly in the text."
    )
    result = invoke_routed(prompt, "extract")

    if not is_valid_extract_response(result):
        return "Could not extract structured entities from the input. Please provide more detail."

    return result


@tool
def suggest_next_action(text: str) -> str:
    """Suggest one next CRM action. Uses real DB history if a doctor is mentioned or found."""
    uid = current_user_id.get()
    doctor_name = extract_name_simple(text)
    history = fetch_doctor_history(doctor_name, uid) if (doctor_name and uid) else []

    if doctor_name and uid and not history:
        return f"Sorry, but there is no entry for {doctor_name} in the CRM."

    if not history:
        try:
            conn = get_connection()
            cur = conn.cursor()
            if uid:
                cur.execute(
                    "SELECT doctor_name, notes FROM interactions "
                    "WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                    (uid,),
                )
            else:
                cur.execute(
                    "SELECT doctor_name, notes FROM interactions ORDER BY created_at DESC LIMIT 1"
                )
            row = cur.fetchone()
            cur.close()
            release_connection(conn)
            if row:
                history = [{"doctor_name": row[0], "notes": row[1]}]
                doctor_name = row[0]
        except Exception:
            pass

    if not history:
        return "No interactions found in the CRM to base a suggestion on."

    notes_text = "\n".join(f"- {r['notes']}" for r in history if r["notes"])
    prompt = (
        f"Based on these logged interactions with {doctor_name}:\n\n"
        f"{notes_text}\n\n"
        f"User request: {text}\n\n"
        f"Suggest one specific next action in one sentence. Use only the context above. Do not invent names or details."
    )
    result = invoke_routed(prompt, "suggest")

    if not is_valid_response(result):
        return "Could not generate a suggestion. Please try again."

    return result


_tools = [log_interaction, edit_interaction, summarize_text, extract_entities, suggest_next_action]

agent_graph = create_react_agent(llm, _tools)
