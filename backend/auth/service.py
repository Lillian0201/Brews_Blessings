import hashlib
import secrets

from src.config import get_env
from src.core.errors import ApiError
from src.core.security import password_matches
from auth.repository import find_login_user

SESSION_COOKIE = "bb_session"


def login(cur, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    if not username or not password:
        raise ApiError(422, "Enter your username and password.")

    user = find_login_user(cur, username)
    if not user or not user["isactive"] or not password_matches(user["password"], password):
        raise ApiError(401, "Invalid username or password.")

    return user


def create_session(cur, user_id: int) -> tuple[str, int]:
    try:
        ttl_hours = int(get_env("BB_SESSION_TTL_HOURS", "8"))
    except ValueError as exc:
        raise RuntimeError("BB_SESSION_TTL_HOURS must be a positive integer") from exc
    if ttl_hours <= 0:
        raise RuntimeError("BB_SESSION_TTL_HOURS must be a positive integer")

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cur.execute("DELETE FROM app_sessions WHERE expires_at <= CURRENT_TIMESTAMP")
    cur.execute(
        "INSERT INTO app_sessions (token_hash, user_id, expires_at) "
        "VALUES (%s, %s, CURRENT_TIMESTAMP + (%s * INTERVAL '1 hour'))",
        (token_hash, user_id, ttl_hours),
    )
    return token, ttl_hours * 60 * 60


def revoke_session(cur, token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cur.execute("DELETE FROM app_sessions WHERE token_hash = %s", (token_hash,))
