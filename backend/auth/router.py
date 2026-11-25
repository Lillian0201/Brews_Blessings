from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from psycopg2.extras import RealDictCursor

from auth.service import login
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.post("/login")
def login_endpoint(
    body: Annotated[Any, Body()] = None,
    cur: Annotated[RealDictCursor, Depends(get_cursor)] = None,
) -> dict:
    return login(cur, body)
