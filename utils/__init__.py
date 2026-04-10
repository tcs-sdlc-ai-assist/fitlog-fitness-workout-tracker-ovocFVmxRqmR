import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token,
    get_user_id_from_token,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    COOKIE_HTTPONLY,
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    COOKIE_PATH,
)
from utils.dependencies import (
    get_db,
    get_current_user,
    get_optional_user,
    require_admin,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "verify_access_token",
    "get_user_id_from_token",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "COOKIE_NAME",
    "COOKIE_MAX_AGE",
    "COOKIE_HTTPONLY",
    "COOKIE_SECURE",
    "COOKIE_SAMESITE",
    "COOKIE_PATH",
    "get_db",
    "get_current_user",
    "get_optional_user",
    "require_admin",
]