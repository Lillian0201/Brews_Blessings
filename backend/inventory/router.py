from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from inventory.service import (
    add_item_service,
    list_inventory_response,
    list_movement_response,
    stock_in_service,
    stock_out_service,
)
from src.core.dependencies import get_current_user, require_owner
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.get("/inventory")
def list_inventory_endpoint(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> list[dict]:
    get_current_user(request, cur)
    return list_inventory_response(cur)


@router.get("/inventory/movements")
def list_movements_endpoint(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
) -> list[dict]:
    get_current_user(request, cur)
    return list_movement_response(cur)


@router.post("/inventory/items", status_code=201)
def add_item_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    owner: dict = Depends(require_owner),
) -> dict:
    response, status = add_item_service(cur, body)
    return JSONResponse(status_code=status, content=response)


@router.post("/inventory/stock-in")
def stock_in_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(get_current_user),
) -> dict:
    return stock_in_service(cur, user, body)


@router.post("/inventory/stock-out")
def stock_out_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(get_current_user),
) -> dict:
    return stock_out_service(cur, user, body)
