import re

_NON_NAME_WORDS = {
    "meeting", "visit", "appointment", "was", "is", "are", "the", "a", "an",
    "and", "or", "discussed", "interested", "met", "about", "for", "with",
    "said", "told", "asked", "mentioned", "noted", "requested", "wanted",
}


def formal_doctor_name(name: str) -> str:
    """Return 'Dr. Title Case Name' regardless of input format."""
    if not name:
        return name
    clean = re.sub(r'^dr\.?\s*', '', name.strip(), flags=re.IGNORECASE).strip()
    if not clean:
        return name
    return 'Dr. ' + ' '.join(w.capitalize() for w in clean.split())


def normalize_doctor_name(name: str) -> str:
    """Return lowercase bare name (no Dr. prefix) — used as dedup key only."""
    name = name.strip().lower()
    name = re.sub(r'^dr\.?\s*', '', name)
    return name.strip()


def extract_name_simple(text: str):
    match = re.search(r"\bDr\.?\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", text, re.IGNORECASE)
    if match:
        parts = match.group(1).strip().split()
        while parts and parts[-1].lower() in _NON_NAME_WORDS:
            parts.pop()
        if parts:
            return formal_doctor_name(' '.join(parts))
    return None


def detect_interaction_type(text: str) -> str:
    """Infer Call / Visit / Meeting from keywords in free text."""
    t = text.lower()
    if any(w in t for w in ('called', 'call', 'phone', 'phoned', 'rang', 'dialled', 'dialed')):
        return 'Call'
    if any(w in t for w in ('visited', 'visit', 'clinic', 'in-person', 'in person', 'stopped by', 'dropped by')):
        return 'Visit'
    return 'Meeting'
