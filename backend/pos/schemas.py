from typing import Any

from pydantic import BaseModel


class OrderItemRequest(BaseModel):
    productId: Any = None
    qty: Any = None
    price: Any = None
    size: Any = None
    shots: Any = None
    sweetness: Any = None
    ice: Any = None
    notes: Any = None


class OrderRequest(BaseModel):
    items: Any = None
    discountPercent: Any = None
    payment: Any = None
    tendered: Any = None
    customer: Any = None


class StatusRequest(BaseModel):
    status: Any = None
    reason: Any = None
