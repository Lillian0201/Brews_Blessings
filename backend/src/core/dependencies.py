from typing import Annotated

from fastapi import Depends, Header, Request
from psycopg2.extensions import connection
from psycopg2.extras import RealDictCursor

from src.core.errors import ApiError
from src.database.connection import get_cursor


def get_current_user(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> dict:
    username = (request.headers.get("X-Username") or "").strip()
    if not username:
        raise ApiError(401, "Not logged in.")
    cur.execute(
        'SELECT userid, fullname, username, role FROM "User" '
        "WHERE lower(username) = lower(%s) AND isactive",
        (username,),
    )
    user = cur.fetchone()
    if not user:
        raise ApiError(401, "Unknown or inactive user.")
    return user


def require_owner(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> dict:
    user = get_current_user(request, cur)
    if user["role"] != "Owner":
        raise ApiError(403, "Only the Owner can do this.")
    return user
