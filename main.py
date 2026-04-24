from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import psycopg2
import os
from dotenv import load_dotenv
from agent import run as agent_run

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_connection():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )


# ── Request schemas ───────────────────────────────────────────────────────────

class StructuredInteractionRequest(BaseModel):
    doctor_name: str
    interaction_type: str = "Meeting"
    date_time: Optional[str] = None
    attendees: Optional[str] = None
    notes: str = ""
    products_discussed: Optional[str] = None
    sentiment: str = "Neutral"
    follow_up: Optional[str] = None

class LogInteractionRequest(BaseModel):
    doctor_name: str
    notes: str

class EditInteractionRequest(BaseModel):
    id: int
    notes: str

class ChatRequest(BaseModel):
    message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "CRM backend is running"}


@app.get("/interactions")
def get_interactions():
    """Return the 20 most recent interactions for the list view."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, doctor_name, interaction_type, notes, sentiment, follow_up, created_at
            FROM interactions
            ORDER BY created_at DESC
            LIMIT 20
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-structured-interaction")
def log_structured_interaction(body: StructuredInteractionRequest):
    """Insert a structured interaction directly — no AI involved."""
    if not body.doctor_name.strip():
        raise HTTPException(status_code=400, detail="doctor_name is required")
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO interactions
                (doctor_name, interaction_type, notes, attendees,
                 products_discussed, sentiment, follow_up, date_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.doctor_name.strip(),
                body.interaction_type,
                body.notes,
                body.attendees,
                body.products_discussed,
                body.sentiment,
                body.follow_up,
                body.date_time,
            ),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Interaction logged", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/log-interaction")
def log_interaction(body: LogInteractionRequest):
    """Legacy endpoint — inserts with doctor_name + notes only."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO interactions (doctor_name, notes) VALUES (%s, %s) RETURNING id",
            (body.doctor_name, body.notes),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Interaction logged", "id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/edit-interaction")
def edit_interaction(body: EditInteractionRequest):
    """Update notes of an existing interaction by id."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE interactions SET notes = %s WHERE id = %s",
            (body.notes, body.id),
        )
        if cur.rowcount == 0:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail=f"No interaction found with id {body.id}")
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Interaction updated", "id": body.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
def chat(body: ChatRequest):
    """Pass the user's message to the LangGraph agent."""
    try:
        response = agent_run(body.message)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
