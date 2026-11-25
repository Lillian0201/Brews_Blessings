import hashlib
from typing import Annotated

from fastapi import Depends, Request
from psycopg2.extras import RealDictCursor

from auth.service import SESSION_COOKIE
from src.core.errors import ApiError
from src.database.connection import get_cursor


def get_current_user(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise ApiError(401, "Not logged in.")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cur.execute(
        'SELECT u.userid, u.fullname, u.username, u.role FROM app_sessions s '
        'JOIN "User" u ON u.userid = s.user_id '
        "WHERE s.token_hash = %s AND s.expires_at > CURRENT_TIMESTAMP AND u.isactive",
        (token_hash,),
    )
    user = cur.fetchone()
    if not user:
        raise ApiError(401, "Session expired or user is inactive.")
    return user


def require_owner(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> dict:
    user = get_current_user(request, cur)
    if user["role"] != "Owner":
        raise ApiError(403, "Only the Owner can do this.")
    return user
