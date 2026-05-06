import os
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException

_SECRET = os.getenv("JWT_SECRET")
if not _SECRET:
    raise ValueError("JWT_SECRET environment variable is not set")
_ALGORITHM = "HS256"
_EXPIRY_HOURS = 1

_pwd = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=_EXPIRY_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
