import re

from src.core.errors import ApiError
from src.core.audit import audit
from src.core.security import hash_password
from users.models import ROLES
from users.repository import (
    active_owner_count,
    add_user,
    get_user,
    list_users,
    update_user,
    username_exists,
)


def clean_text(value, label: str, max_len: int = 45) -> str:
    text = str(value or "").strip()
    if not text:
        raise ApiError(422, f"{label} is required.")
    if len(text) > max_len:
        raise ApiError(422, f"{label} is too long ({max_len} characters max).")
    return text


def serialize_user(row: dict) -> dict:
    return {
        "id": row["userid"],
        "name": row["fullname"],
        "username": row["username"],
        "role": row["role"],
        "active": row["isactive"],
    }


def get_user_response(cur, user_id: int) -> dict:
    row = get_user(cur, user_id)
    if not row:
        raise ApiError(404, "User not found.")
    return serialize_user(row)


def list_user_response(cur) -> list[dict]:
    return [serialize_user(row) for row in list_users(cur)]


def add_user_service(cur, owner: dict, body: dict | None) -> tuple[dict, int]:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    name = clean_text(body.get("name"), "Full name")
    username = str(body.get("username") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{3,45}", username):
        raise ApiError(422, "Username must be 3 to 45 letters, numbers, dots, dashes or underscores.")
    role = body.get("role")
    if role not in ROLES:
        raise ApiError(422, "Role must be Owner or Barista.")
    password = str(body.get("password") or "")
    if len(password) < 6:
        raise ApiError(422, "Password must be at least 6 characters.")
    if len(password) > 128:
        raise ApiError(422, "Password is too long.")
    if username_exists(cur, username):
        raise ApiError(409, f"The username {username} is already taken.")
    user_id = add_user(cur, name, username, hash_password(password), role)
    audit(cur, owner["userid"], f"Added user {username} ({role})", "USER", user_id)
    return get_user_response(cur, user_id), 201


def update_user_service(cur, owner: dict, user_id: int, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    target = get_user_response(cur, user_id)
    name = clean_text(body["name"], "Full name") if "name" in body else target["name"]
    role = body["role"] if "role" in body else target["role"]
    if role not in ROLES:
        raise ApiError(422, "Role must be Owner or Barista.")
    active = bool(body["active"]) if "active" in body else target["active"]
    if user_id == owner["userid"] and not active:
        raise ApiError(409, "You can't deactivate your own account.")
    loses_owner = target["role"] == "Owner" and target["active"] and (role != "Owner" or not active)
    if loses_owner and active_owner_count(cur, user_id) == 0:
        raise ApiError(409, "There must be at least one active Owner.")
    update_user(cur, user_id, name, role, active)
    what = "Activated" if active and not target["active"] else "Deactivated" if target["active"] and not active else "Updated"
    audit(cur, owner["userid"], f"{what} user {target['username']}", "USER", user_id)
    return get_user_response(cur, user_id)
