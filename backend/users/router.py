from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from src.core.dependencies import require_owner
from src.database.connection import get_cursor
from users.service import add_user_service, list_user_response, update_user_service


router = APIRouter(prefix="/api")


@router.get("/users")
def list_users_endpoint(
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    _owner: dict = Depends(require_owner),
) -> list[dict]:
    return list_user_response(cur)


@router.post("/users", status_code=201)
def add_user_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    response, status = add_user_service(cur, owner, body)
    return JSONResponse(status_code=status, content=response)


@router.put("/users/{user_id}")
def update_user_endpoint(
    user_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    return update_user_service(cur, owner, user_id, body)
