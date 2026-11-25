from src.core.errors import ApiError
from src.core.security import password_matches
from auth.repository import find_login_user


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

    return {
        "userid": user["userid"],
        "fullname": user["fullname"],
        "username": user["username"],
        "role": user["role"],
    }
