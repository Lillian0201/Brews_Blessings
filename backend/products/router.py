from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from products.service import (
    add_product_service,
    delete_product_service,
    list_product_response,
    update_product_service,
)
from src.core.dependencies import get_current_user, require_admin_or_owner
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.get("/products")
def list_products_endpoint(
    request: Request,
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    available: str | None = None,
) -> list[dict]:
    get_current_user(request, cur)
    return list_product_response(cur, True if available == "true" else None)


@router.post("/products", status_code=201)
def add_product_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(require_admin_or_owner),
) -> dict:
    response, status = add_product_service(cur, user, body)
    return JSONResponse(status_code=status, content=response)


@router.put("/products/{product_id}")
def update_product_endpoint(
    product_id: int,
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(require_admin_or_owner),
) -> dict:
    return update_product_service(cur, user, product_id, body)


@router.delete("/products/{product_id}")
def delete_product_endpoint(
    product_id: int,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
    user: dict = Depends(require_admin_or_owner),
) -> dict:
    return delete_product_service(cur, user, product_id)
