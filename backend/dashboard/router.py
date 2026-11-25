from typing import Annotated

from fastapi import APIRouter, Depends
from psycopg2.extras import RealDictCursor

from dashboard.service import dashboard_summary
from src.core.dependencies import get_current_user
from src.database.connection import get_cursor


router = APIRouter(prefix="/api")


@router.get("/dashboard/summary")
def dashboard_endpoint(
    cur: Annotated[RealDictCursor, Depends(get_cursor)],
    _user: dict = Depends(get_current_user),
) -> dict:
    return dashboard_summary(cur)
