import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

SECRET_KEY: str = os.getenv("SECRET_KEY", "fitlog-dev-secret-key-change-in-production")
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

COOKIE_NAME: str = "fitlog_access_token"
COOKIE_MAX_AGE: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60
COOKIE_HTTPONLY: bool = True
COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
COOKIE_SAMESITE: str = "lax"
COOKIE_PATH: str = "/"


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Optional[dict]:
    try:
        payload: dict = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    payload = verify_access_token(token)
    if payload is None:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (ValueError, TypeError):
        return None