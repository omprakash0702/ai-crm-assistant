import logging
from difflib import SequenceMatcher
from app.db.connection import get_connection, release_connection

logger = logging.getLogger(__name__)


def get_or_create_doctor(name: str, user_id: int) -> int:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM doctors WHERE LOWER(name) = LOWER(%s) AND user_id = %s",
            (name, user_id),
        )
        row = cur.fetchone()
        if row:
            doctor_id = row[0]
        else:
            cur.execute(
                "INSERT INTO doctors (name, user_id) VALUES (%s, %s) "
                "ON CONFLICT (LOWER(name), user_id) DO UPDATE SET name = EXCLUDED.name "
                "RETURNING id",
                (name, user_id),
            )
            doctor_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return doctor_id
    except Exception:
        logger.error("get_or_create_doctor failed for name=%s user_id=%s", name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def update_doctor_stats(doctor_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE doctors
            SET last_visit = NOW(),
                total_interactions = (
                    SELECT COUNT(*) FROM interactions WHERE doctor_id = %s
                )
            WHERE id = %s
            """,
            (doctor_id, doctor_id),
        )
        conn.commit()
        cur.close()
    except Exception:
        logger.error("update_doctor_stats failed for doctor_id=%s", doctor_id, exc_info=True)
    finally:
        release_connection(conn)


def fetch_doctor_history(name: str, user_id: int = None) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        search = f"%{name.replace('Dr.', '').replace('dr.', '').strip()}%"
        if user_id is not None:
            cur.execute(
                "SELECT id, doctor_name, notes, created_at FROM interactions "
                "WHERE LOWER(doctor_name) LIKE LOWER(%s) AND user_id = %s "
                "ORDER BY created_at DESC LIMIT 5",
                (search, user_id),
            )
        else:
            cur.execute(
                "SELECT id, doctor_name, notes, created_at FROM interactions "
                "WHERE LOWER(doctor_name) LIKE LOWER(%s) "
                "ORDER BY created_at DESC LIMIT 5",
                (search,),
            )
        rows = cur.fetchall()
        cur.close()
        return [{"id": r[0], "doctor_name": r[1], "notes": r[2], "created_at": str(r[3])} for r in rows]
    except Exception:
        logger.error("fetch_doctor_history failed for name=%s", name, exc_info=True)
        return []
    finally:
        release_connection(conn)


def is_duplicate(text: str, user_id: int = None) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        if user_id is not None:
            cur.execute(
                "SELECT notes FROM interactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
                (user_id,),
            )
        else:
            cur.execute("SELECT notes FROM interactions ORDER BY created_at DESC LIMIT 20")
        rows = cur.fetchall()
        cur.close()
        for (existing_notes,) in rows:
            if existing_notes and SequenceMatcher(None, text.lower(), existing_notes.lower()).ratio() >= 0.85:
                return True
        return False
    except Exception:
        logger.error("is_duplicate check failed", exc_info=True)
        return False
    finally:
        release_connection(conn)
