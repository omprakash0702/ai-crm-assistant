import re
from app.db.queries import fetch_doctor_history
from app.core.context import current_user_id

VALID_SENTIMENTS = {"Positive", "Negative", "Neutral"}

_NULL_VALUES = {"unknown", "none", "n/a", "—", "-", ""}
_EXTRACT_FIELDS = ("doctor:", "product:", "location:", "date:")


def is_valid_sentiment(value: str) -> bool:
    return value in VALID_SENTIMENTS


def is_valid_name(name: str) -> bool:
    return bool(name) and name.strip().lower() not in _NULL_VALUES


def is_valid_response(response: str) -> bool:
    return bool(response and response.strip())


def is_valid_extract_response(response: str) -> bool:
    lower = response.lower()
    return all(field in lower for field in _EXTRACT_FIELDS)


def doctor_exists_in_db(doctor_name: str) -> bool:
    if not is_valid_name(doctor_name):
        return False
    uid = current_user_id.get()
    return len(fetch_doctor_history(doctor_name, uid)) > 0


def parse_doctor_from_extract(response: str):
    """Parse the Doctor field value out of an extract_entities LLM response."""
    match = re.search(r"^doctor:\s*(.+)", response, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    name = match.group(1).strip()
    return None if name == "—" or name.lower() in _NULL_VALUES else name
