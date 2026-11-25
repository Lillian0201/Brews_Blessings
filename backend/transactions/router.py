from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from psycopg2.extras import RealDictCursor

from src.core.dependencies import get_current_user, require_owner
from src.database.connection import get_cursor
from transactions.service import (
    approve_refund,
    get_sale,
    list_refund_response,
    list_sales,
    reject_refund_service,
    request_refund,
    void_sale,
)
from fastapi.responses import JSONResponse


router = APIRouter(prefix="/api")


@router.get("/transactions")
def list_transactions_endpoint(
    tab: str = "sales",
    payment: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: str = "500",
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    _owner: dict = Depends(require_owner),
) -> list[dict]:
    try:
        limit = min(max(int(limit), 1), 1000)
    except (TypeError, ValueError):
        from src.core.errors import ApiError
        raise ApiError(422, "limit must be a number.")
    return list_sales(cur, tab, payment, q, date_from, date_to, limit)


@router.get("/transactions/{order_id}")
def get_transaction_endpoint(
    order_id: int,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    _owner: dict = Depends(require_owner),
) -> dict:
    return get_sale(cur, order_id)


@router.get("/refunds")
def list_refunds_endpoint(
    status: str | None = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    _owner: dict = Depends(require_owner),
) -> list[dict]:
    return list_refund_response(cur, status)


@router.post("/transactions/{order_id}/refunds", status_code=201)
def request_refund_endpoint(
    order_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(get_current_user),
) -> dict:
    return JSONResponse(status_code=201, content=request_refund(cur, user, order_id, body))


@router.post("/refunds/{refund_id}/approve")
def approve_refund_endpoint(
    refund_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    return approve_refund(cur, owner, refund_id, body)


@router.post("/refunds/{refund_id}/reject")
def reject_refund_endpoint(
    refund_id: int,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    return reject_refund_service(cur, owner, refund_id)


@router.post("/transactions/{order_id}/void")
def void_sale_endpoint(
    order_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    return void_sale(cur, owner, order_id, body)
