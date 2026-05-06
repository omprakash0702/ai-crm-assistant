import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.db.connection import get_connection, release_connection
from app.core.security import decode_token

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_user_by_api_key(api_key: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE api_key = %s", (api_key,))
        row = cur.fetchone()
        cur.close()
        return {"id": row[0], "name": row[1]} if row else None
    except Exception:
        logger.error("API key lookup failed", exc_info=True)
        return None
    finally:
        release_connection(conn)


def _get_user_by_id(user_id: int):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        return {"id": row[0], "name": row[1]} if row else None
    except Exception:
        logger.error("User-by-id lookup failed", exc_info=True)
        return None
    finally:
        release_connection(conn)


def _get_user_by_email(email: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, name, hashed_password FROM users WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        return {"id": row[0], "name": row[1], "hashed_password": row[2]} if row else None
    except Exception:
        logger.error("User-by-email lookup failed", exc_info=True)
        return None
    finally:
        release_connection(conn)


# ── API-key middleware (keeps existing routes working) ────────────────────────

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        request.state.user = _get_user_by_api_key(api_key) if api_key else None
        return await call_next(request)


def require_user(request: Request):
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key")
    return user


# ── JWT dependency ────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    user_id = decode_token(credentials.credentials)
    user = _get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
