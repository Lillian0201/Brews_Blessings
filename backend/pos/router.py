from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from pos.service import create_order_service, get_order_response, list_order_response, set_status_service
from src.core.dependencies import get_current_user
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.post("/orders", status_code=201)
def create_order_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(get_current_user),
) -> dict:
    response, status = create_order_service(cur, user, body)
    return JSONResponse(status_code=status, content=response)


@router.get("/orders")
def list_orders_endpoint(
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    _user: dict = Depends(get_current_user),
) -> list[dict]:
    return list_order_response(cur)


@router.get("/orders/{order_id}")
def get_order_endpoint(
    order_id: int,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    _user: dict = Depends(get_current_user),
) -> dict:
    return get_order_response(cur, order_id)


@router.patch("/orders/{order_id}/status")
def set_status_endpoint(
    order_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(get_current_user),
) -> dict:
    return set_status_service(cur, user, order_id, body)
