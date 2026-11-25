from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from expenses.service import add_expense_service, list_expense_response
from src.core.errors import ApiError
from src.core.dependencies import require_owner
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.get("/expenses")
def list_expenses_endpoint(
    type: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: str = "500",
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> list[dict]:
    try:
        limit = min(max(int(limit), 1), 1000)
    except (TypeError, ValueError):
        raise ApiError(422, "limit must be a number.")
    return list_expense_response(cur, type, date_from, date_to, limit)


@router.post("/expenses", status_code=201)
def add_expense_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    response, status = add_expense_service(cur, owner, body)
    return JSONResponse(status_code=status, content=response)
