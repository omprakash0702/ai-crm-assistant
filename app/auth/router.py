import logging
from fastapi import APIRouter, HTTPException

from app.core.auth import _get_user_by_email
from app.core.security import hash_password, verify_password, create_token
from app.db.connection import get_connection, release_connection
from app.models.schemas import SignupRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


@router.post("/signup", status_code=201)
def signup(body: SignupRequest):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Email already registered")
        cur.execute(
            """
            INSERT INTO users (name, email, hashed_password, company, job_title, territory)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                body.name,
                body.email,
                hash_password(body.password),
                body.company,
                body.job_title,
                body.territory,
            ),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        token = create_token(user_id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {"id": user_id, "name": body.name, "email": body.email},
        }
    except HTTPException:
        raise
    except Exception:
        logger.error("signup failed", exc_info=True)
        try:
            conn.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Signup failed, please try again")
    finally:
        release_connection(conn)


@router.post("/login")
def login(body: LoginRequest):
    user = _get_user_by_email(body.email)
    if not user or not user.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user["id"])
    return {"access_token": token, "token_type": "bearer"}
