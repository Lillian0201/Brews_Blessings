import os
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, Response
from psycopg2.extras import RealDictCursor

from auth.service import SESSION_COOKIE, create_session, login, revoke_session
from src.core.dependencies import get_current_user
from src.config import get_bool
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.post("/login")
def login_endpoint(
    response: Response,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    body: Annotated[Any, Body()] = None,
) -> dict:
    user = login(cur, body)
    token, max_age = create_session(cur, user["userid"])
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=max_age,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    return {
        "userid": user["userid"],
        "fullname": user["fullname"],
        "username": user["username"],
        "role": user["role"],
    }


@router.get("/me")
def current_user_endpoint(
    user: Annotated[dict, Depends(get_current_user)],
) -> dict:
    return {
        "userid": user["userid"],
        "fullname": user["fullname"],
        "username": user["username"],
        "role": user["role"],
    }


@router.post("/logout", status_code=204)
def logout_endpoint(
    request: Request,
    response: Response,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> Response:
    revoke_session(cur, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=_cookie_secure(),
        samesite="strict",
        path="/",
    )
    response.status_code = 204
    return response


def _cookie_secure() -> bool:
    return get_bool("BB_COOKIE_SECURE", os.getenv("VERCEL") == "1")
