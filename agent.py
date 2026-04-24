"""
CRM AI Agent  (agent.py)
========================
Routing is done entirely in Python via keyword matching.
The LLM is only called inside tool functions that need language generation.
"""

import os
import re
import psycopg2
from difflib import SequenceMatcher
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

load_dotenv()

llm = ChatGroq(model="llama-3.1-8b-instant")

SYSTEM_PROMPT = """You are a CRM data assistant. Be precise, brief, and factual.

STRICT RULES — NO EXCEPTIONS:
- Never use: "It seems", "It looks like", "It appears", "I think", "Perhaps", "Probably"
- Never add information not present in the input
- Never hallucinate names, products, locations, or outcomes
- Never use narrative language: "great interaction", "glad to report", "positive experience"
- Keep responses to 1–2 sentences unless the task requires more
- Do only what the specific task asks — nothing more
- If information is missing, do not guess or fill in"""


def _invoke(prompt: str) -> str:
    return llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]).content



# ---------------------------------------------------------------------------
# DB helper
# ---------------------------------------------------------------------------
def get_db():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )



# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_NON_NAME_WORDS = {
    "meeting", "visit", "appointment", "was", "is", "are", "the", "a", "an",
    "and", "or", "discussed", "interested", "met", "about", "for", "with",
    "said", "told", "asked", "mentioned", "noted", "requested", "wanted",
}

def _extract_name_simple(text: str):
    """Extract doctor name from text using regex — no LLM."""
    match = re.search(r"\bDr\.?\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
    if match:
        parts = match.group(1).strip().split()
        while parts and parts[-1].lower() in _NON_NAME_WORDS:
            parts.pop()
        if parts:
            return "Dr. " + " ".join(p.title() for p in parts)
    return None


def _fetch_doctor_history(name: str) -> list:
    """Fetch recent interactions for a doctor from the DB."""
    try:
        conn = get_db()
        cur = conn.cursor()
        search = f"%{name.replace('Dr.', '').replace('dr.', '').strip()}%"
        cur.execute(
            "SELECT id, doctor_name, notes, created_at FROM interactions "
            "WHERE LOWER(doctor_name) LIKE LOWER(%s) ORDER BY created_at DESC LIMIT 5",
            (search,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"id": r[0], "doctor_name": r[1], "notes": r[2], "created_at": str(r[3])} for r in rows]
    except Exception:
        return []


def _is_duplicate(text: str) -> bool:
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT notes FROM interactions ORDER BY created_at DESC LIMIT 20")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        for (existing_notes,) in rows:
            if existing_notes and SequenceMatcher(None, text.lower(), existing_notes.lower()).ratio() >= 0.85:
                return True
        return False
    except Exception:
        return False


@tool
def log_interaction(text: str) -> str:
    """Log a new doctor interaction to the CRM. Use when the user describes a meeting, visit, or call with a doctor."""
    force = bool(re.match(r"^new\s+entry\s*:", text, re.IGNORECASE))
    if force:
        text = re.sub(r"^new\s+entry\s*:\s*", "", text, flags=re.IGNORECASE).strip()

    if not force and _is_duplicate(text):
        return (
            "This interaction already appears to be logged. "
            "Do you want to create a new entry? "
            "If yes, resend your message starting with: new entry: ..."
        )

    prompt = (
        "Extract from this CRM note. Return exactly 4 lines, no extra text:\n"
        "Doctor: <Dr. LastName only — do NOT include words like 'meeting', 'visit', 'appointment'. If no name, write Unknown>\n"
        "Sentiment: <Positive ONLY if clearly satisfied/agreed | Negative ONLY if clearly unhappy/refused | else Neutral>\n"
        "Follow-up: <one action, max 8 words, from the text only>\n"
        "Summary: <one sentence, facts from text only>\n\n"
        f"Text: {text}\n\n"
        "Use only facts from the text. Do not add anything."
    )
    result = _invoke(prompt)

    doctor_name = "Unknown"
    sentiment = "Neutral"
    follow_up = "Schedule a follow-up meeting."
    summary = text[:120]

    for line in result.splitlines():
        line = line.strip()
        if line.lower().startswith("doctor:"):
            name = line.split(":", 1)[1].strip()
            if name.lower() not in ("unknown", "none", "n/a"):
                doctor_name = name if name.lower().startswith("dr.") else f"Dr. {name}"
        elif line.lower().startswith("sentiment:"):
            val = line.split(":", 1)[1].strip()
            if val in ("Positive", "Negative", "Neutral"):
                sentiment = val
        elif line.lower().startswith("follow-up:") or line.lower().startswith("follow up:"):
            follow_up = line.split(":", 1)[1].strip()
        elif line.lower().startswith("summary:"):
            summary = line.split(":", 1)[1].strip()

    if doctor_name == "Unknown":
        regex_name = _extract_name_simple(text)
        if regex_name:
            doctor_name = regex_name

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO interactions (doctor_name, notes) VALUES (%s, %s) RETURNING id",
            (doctor_name, text),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return (
            f"Interaction #{new_id} logged for {doctor_name}. "
            f"{summary} "
            f"Sentiment: {sentiment}. Follow-up: {follow_up}"
        )
    except Exception as e:
        return f"Failed to log interaction: {e}"


@tool
def edit_interaction(text: str) -> str:
    """Edit the notes of an existing interaction. Requires a numeric interaction ID in the text."""
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
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT doctor_name FROM interactions WHERE id = %s", (record_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return "Invalid interaction ID."
        doctor_name = row[0]
        cur.execute("UPDATE interactions SET notes = %s WHERE id = %s", (notes, record_id))
        conn.commit()
        cur.close()
        conn.close()
        return f"Interaction #{record_id} for {doctor_name} updated — notes: {notes}"
    except Exception as e:
        return f"Failed to edit interaction: {e}"


@tool
def summarize_text(text: str) -> str:
    """Summarize interaction notes. Fetches real notes from DB if a doctor name is mentioned."""
    doctor_name = _extract_name_simple(text)
    history = _fetch_doctor_history(doctor_name) if doctor_name else []

    if doctor_name and not history:
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
    return _invoke(prompt)


@tool
def extract_entities(text: str) -> str:
    """Extract doctor name, product, location, and date. Enriches with DB history if doctor is already logged."""
    doctor_name = _extract_name_simple(text)
    history = _fetch_doctor_history(doctor_name) if doctor_name else []

    db_context = ""
    if doctor_name and not history:
        db_context = f"\n\nNote: {doctor_name} has no logged interactions in the CRM."
    elif history:
        db_context = (
            f"\n\nThis doctor has {len(history)} logged interaction(s) in the CRM. "
            f"Most recent note: \"{history[0]['notes']}\""
        )

    prompt = (
        "Extract only what is explicitly mentioned in the text below.\n"
        "Start with one brief sentence stating who was met and what was discussed.\n"
        "Then list on separate lines:\n"
        "Doctor: [name or —]\n"
        "Product: [name or —]\n"
        "Location: [name or —]\n"
        "Date: [date or —]\n\n"
        f"Text: {text}{db_context}\n\n"
        "For any missing field, write exactly: —\n"
        "Do not infer or add anything not directly stated."
    )
    return _invoke(prompt)


@tool
def suggest_next_action(text: str) -> str:
    """Suggest one next CRM action. Uses real DB history if a doctor is mentioned or found."""
    doctor_name = _extract_name_simple(text)
    history = _fetch_doctor_history(doctor_name) if doctor_name else []

    if doctor_name and not history:
        return f"Sorry, but there is no entry for {doctor_name} in the CRM."

    if not history:
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                "SELECT doctor_name, notes FROM interactions ORDER BY created_at DESC LIMIT 1"
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
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
    return _invoke(prompt)


# ---------------------------------------------------------------------------
# LangGraph agent  — 5 tools registered
# ---------------------------------------------------------------------------
_tools = [log_interaction, edit_interaction, summarize_text, extract_entities, suggest_next_action]

agent_graph = create_react_agent(llm, _tools)


# ---------------------------------------------------------------------------
# Deterministic router  — zero LLM calls, instant dispatch
# ---------------------------------------------------------------------------
_EDIT_WORDS      = ("update", "edit", "change", "correct", "fix", "modify")
_SUMMARIZE_WORDS = ("summarize", "summary", "shorten", "condense", "brief")
_EXTRACT_WORDS   = ("extract", "pull out", "identify", "list the", "what doctor",
                    "which medicine", "what product")
_SUGGEST_WORDS   = ("next step", "what should i do", "suggest", "recommend",
                    "follow up", "follow-up", "what now", "advice", "plan")


def _route(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in _EDIT_WORDS) and re.search(r"\b\d+\b", lower):
        return "edit"
    if any(w in lower for w in _SUMMARIZE_WORDS):
        return "summarize"
    if any(w in lower for w in _EXTRACT_WORDS):
        return "extract"
    if any(w in lower for w in _SUGGEST_WORDS):
        return "suggest"
    return "log"


# ---------------------------------------------------------------------------
# run()  — routes deterministically, calls tools directly
# ---------------------------------------------------------------------------
_CONFIRMATION_WORDS = {"yes", "yeah", "y", "confirm", "ok", "okay", "sure", "yep"}

def run(user_input: str) -> str:
    if user_input.strip().lower() in _CONFIRMATION_WORDS:
        return (
            "To create a new entry, please resend your original message with the prefix:\n"
            "new entry: <your message>\n\n"
            "Example: new entry: Met Dr. Patel, discussed Metformin"
        )
    route = _route(user_input)
    if route == "edit":
        return edit_interaction.invoke(user_input)
    if route == "summarize":
        return summarize_text.invoke(user_input)
    if route == "extract":
        return extract_entities.invoke(user_input)
    if route == "suggest":
        return suggest_next_action.invoke(user_input)
    return log_interaction.invoke(user_input)


# ---------------------------------------------------------------------------
# Quick terminal test:  python agent.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("CRM Agent ready. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input or user_input.lower() in ("quit", "exit"):
            break
        print(f"\nAgent: {run(user_input)}\n")
