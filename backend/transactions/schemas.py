from typing import Any

from pydantic import BaseModel


class RefundRequest(BaseModel):
    item: Any = None
    amount: Any = None
    reason: Any = None
    itemReturned: Any = None


class VoidRequest(BaseModel):
    reason: Any = None
