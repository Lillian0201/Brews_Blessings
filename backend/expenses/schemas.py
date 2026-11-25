from typing import Any

from pydantic import BaseModel


class ExpenseRequest(BaseModel):
    type: Any = None
    description: Any = None
    amount: Any = None
    date: Any = None
