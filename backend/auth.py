"""
Login API. Checks the username and password against the hashed Password
column in the User table and returns the user's role.

The frontend keeps the logged-in username and sends it in the X-Username
header, which transactions.py already reads. Replace that header with a
signed token before deployment.
"""
from flask import Blueprint, jsonify
from werkzeug.security import check_password_hash

from db import get_conn  # noqa: F401  (with_db opens the connection)
from transactions import ApiError, handle_api_error, json_body, with_db

bp = Blueprint("auth", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)


def password_matches(stored, given):
    try:
        return check_password_hash(stored, given)
    except ValueError:
        # The stored value isn't a hash, for example a plain-text password
        return False


@bp.post("/login")
@with_db
def login(cur):
    body = json_body()
    username = str(body.get("username") or "").strip()
    password = str(body.get("password") or "")
    if not username or not password:
        raise ApiError(422, "Enter your username and password.")

    cur.execute(
        'SELECT userid, fullname, username, role, password, isactive FROM "User" '
        "WHERE lower(username) = lower(%s)",
        (username,),
    )
    user = cur.fetchone()

    # Same message for an unknown user, a wrong password, and an inactive account
    if not user or not user["isactive"] or not password_matches(user["password"], password):
        raise ApiError(401, "Invalid username or password.")

    return jsonify({
        "userid": user["userid"],
        "fullname": user["fullname"],
        "username": user["username"],
        "role": user["role"],
    })