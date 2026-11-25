from typing import Any

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    todaySales: Any
    refunds: Any
