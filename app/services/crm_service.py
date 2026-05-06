import logging
from app.db.connection import get_connection, release_connection
from app.db.queries import get_or_create_doctor, update_doctor_stats
from app.utils.text import normalize_doctor_name, formal_doctor_name

logger = logging.getLogger(__name__)


def get_interactions(user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, doctor_name, interaction_type, notes, sentiment, follow_up, created_at
            FROM interactions
            WHERE doctor_id IS NOT NULL AND user_id = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "doctor_name": r[1],
                "interaction_type": r[2],
                "notes": r[3],
                "sentiment": r[4],
                "follow_up": r[5],
                "created_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    except Exception:
        logger.error("get_interactions failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def log_structured_interaction(
    doctor_name: str,
    interaction_type: str,
    notes: str,
    attendees,
    products_discussed,
    sentiment: str,
    follow_up,
    date_time,
    user_id: int,
) -> int:
    formal = formal_doctor_name(doctor_name)
    doctor_id = get_or_create_doctor(normalize_doctor_name(formal), user_id)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interactions
                (doctor_name, interaction_type, notes, attendees,
                 products_discussed, sentiment, follow_up, date_time, doctor_id, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (formal, interaction_type, notes, attendees, products_discussed,
             sentiment, follow_up, date_time, doctor_id, user_id),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        update_doctor_stats(doctor_id)
        return new_id
    except Exception:
        logger.error("log_structured_interaction failed for doctor=%s user_id=%s", doctor_name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def log_interaction_basic(doctor_name: str, notes: str, user_id: int) -> int:
    formal = formal_doctor_name(doctor_name)
    doctor_id = get_or_create_doctor(normalize_doctor_name(formal), user_id)
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO interactions (doctor_name, notes, doctor_id, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
            (formal, notes, doctor_id, user_id),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        update_doctor_stats(doctor_id)
        return new_id
    except Exception:
        logger.error("log_interaction_basic failed for doctor=%s user_id=%s", doctor_name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def edit_interaction_basic(record_id: int, notes: str, user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE interactions SET notes = %s WHERE id = %s AND user_id = %s",
            (notes, record_id, user_id),
        )
        updated = cur.rowcount > 0
        conn.commit()
        cur.close()
        return updated
    except Exception:
        logger.error("edit_interaction_basic failed for id=%s user_id=%s", record_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


# ── Metrics ──────────────────────────────────────────────────────────────────

def get_metrics_summary(user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM interactions WHERE doctor_id IS NOT NULL AND user_id = %s",
            (user_id,),
        )
        total_interactions = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM doctors WHERE user_id = %s", (user_id,))
        total_doctors = cur.fetchone()[0]
        avg = round(total_interactions / total_doctors, 2) if total_doctors > 0 else 0
        cur.close()
        return {
            "total_interactions": total_interactions,
            "total_doctors": total_doctors,
            "avg_interactions_per_doctor": avg,
        }
    except Exception:
        logger.error("get_metrics_summary failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_sentiment_trend(user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                DATE(created_at) AS date,
                COUNT(*) FILTER (WHERE sentiment = 'Positive')                        AS positive,
                COUNT(*) FILTER (WHERE sentiment = 'Negative')                        AS negative,
                COUNT(*) FILTER (WHERE sentiment = 'Neutral' OR sentiment IS NULL)    AS neutral
            FROM interactions
            WHERE doctor_id IS NOT NULL AND user_id = %s
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "date": str(r[0]),
                "positive": r[1],
                "negative": r[2],
                "neutral": r[3],
            }
            for r in rows
        ]
    except Exception:
        logger.error("get_sentiment_trend failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_followup_metrics(user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT d.name, f.task, f.status
            FROM follow_up_tasks f
            JOIN doctors d ON f.doctor_id = d.id
            WHERE f.user_id = %s
            ORDER BY d.name
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [{"doctor_name": r[0], "task": r[1], "status": r[2]} for r in rows]
    except Exception:
        logger.error("get_followup_metrics failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_top_doctors(user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT name, total_interactions
            FROM doctors
            WHERE user_id = %s
            ORDER BY total_interactions DESC
            LIMIT 5
        """, (user_id,))
        rows = cur.fetchall()
        cur.close()
        return [{"name": r[0], "interaction_count": r[1]} for r in rows]
    except Exception:
        logger.error("get_top_doctors failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


# ── Doctor profile ───────────────────────────────────────────────────────────

def get_doctor_profile(name: str, user_id: int) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, last_visit, total_interactions FROM doctors "
            "WHERE LOWER(name) = LOWER(%s) AND user_id = %s",
            (name, user_id),
        )
        doctor = cur.fetchone()
        if not doctor:
            cur.close()
            return None
        doctor_id, doctor_name, last_visit, total_interactions = doctor
        cur.execute(
            "SELECT notes FROM interactions WHERE doctor_id = %s AND user_id = %s ORDER BY created_at DESC LIMIT 5",
            (doctor_id, user_id),
        )
        notes = [row[0] for row in cur.fetchall()]
        cur.close()
        return {
            "name": doctor_name,
            "total_interactions": total_interactions,
            "last_visit": last_visit.isoformat() if last_visit else None,
            "recent_notes": notes,
        }
    except Exception:
        logger.error("get_doctor_profile failed for name=%s user_id=%s", name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_doctor_timeline(name: str, user_id: int) -> list | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        # name comes directly from doctors.name so a case-insensitive exact match is sufficient
        cur.execute(
            "SELECT id FROM doctors WHERE LOWER(name) = LOWER(%s) AND user_id = %s",
            (name, user_id),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            return None
        doctor_id = row[0]
        cur.execute(
            """
            SELECT id, interaction_type, notes, sentiment, follow_up,
                   products_discussed, created_at
            FROM interactions
            WHERE doctor_id = %s AND user_id = %s
            ORDER BY created_at DESC
            """,
            (doctor_id, user_id),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "interaction_type": r[1],
                "notes": r[2],
                "sentiment": r[3],
                "follow_up": r[4],
                "products_discussed": r[5],
                "date_time": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
    except Exception:
        logger.error("get_doctor_timeline failed for name=%s user_id=%s", name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


# ── Doctor CRUD ───────────────────────────────────────────────────────────────

def get_all_doctors(user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, last_visit, total_interactions FROM doctors "
            "WHERE user_id = %s ORDER BY name",
            (user_id,),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "name": r[1],
                "last_visit": r[2].isoformat() if r[2] else None,
                "total_interactions": r[3],
            }
            for r in rows
        ]
    except Exception:
        logger.error("get_all_doctors failed for user_id=%s", user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def create_doctor_record(name: str, user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO doctors (name, user_id) VALUES (%s, %s) "
            "RETURNING id, name, last_visit, total_interactions",
            (name, user_id),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        return {"id": row[0], "name": row[1], "last_visit": None, "total_interactions": row[3]}
    except Exception:
        logger.error("create_doctor_record failed for name=%s user_id=%s", name, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_doctor_by_id(doctor_id: int, user_id: int) -> dict | None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, last_visit, total_interactions FROM doctors "
            "WHERE id = %s AND user_id = %s",
            (doctor_id, user_id),
        )
        row = cur.fetchone()
        cur.close()
        if not row:
            return None
        return {
            "id": row[0],
            "name": row[1],
            "last_visit": row[2].isoformat() if row[2] else None,
            "total_interactions": row[3],
        }
    except Exception:
        logger.error("get_doctor_by_id failed for doctor_id=%s user_id=%s", doctor_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


# ── Follow-up CRUD ────────────────────────────────────────────────────────────

def create_followup(doctor_id: int, task: str, due_date, status: str, user_id: int) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO follow_up_tasks (doctor_id, task, due_date, status, user_id) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (doctor_id, task, due_date, status, user_id),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        return {
            "id": new_id,
            "doctor_id": doctor_id,
            "task": task,
            "due_date": str(due_date) if due_date else None,
            "status": status,
        }
    except Exception:
        logger.error("create_followup failed for doctor_id=%s user_id=%s", doctor_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def get_followups_by_doctor(doctor_id: int, user_id: int) -> list:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, doctor_id, task, due_date, status FROM follow_up_tasks "
            "WHERE doctor_id = %s AND user_id = %s ORDER BY due_date",
            (doctor_id, user_id),
        )
        rows = cur.fetchall()
        cur.close()
        return [
            {
                "id": r[0],
                "doctor_id": r[1],
                "task": r[2],
                "due_date": str(r[3]) if r[3] else None,
                "status": r[4],
            }
            for r in rows
        ]
    except Exception:
        logger.error("get_followups_by_doctor failed for doctor_id=%s user_id=%s", doctor_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def update_followup_status(followup_id: int, status: str, user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE follow_up_tasks SET status = %s WHERE id = %s AND user_id = %s",
            (status, followup_id, user_id),
        )
        updated = cur.rowcount > 0
        conn.commit()
        cur.close()
        return updated
    except Exception:
        logger.error("update_followup_status failed for followup_id=%s user_id=%s", followup_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)


def delete_followup(followup_id: int, user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM follow_up_tasks WHERE id = %s AND user_id = %s",
            (followup_id, user_id),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        cur.close()
        return deleted
    except Exception:
        logger.error("delete_followup failed for followup_id=%s user_id=%s", followup_id, user_id, exc_info=True)
        raise
    finally:
        release_connection(conn)
