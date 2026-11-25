from typing import Any

from pydantic import BaseModel


class ProductRequest(BaseModel):
    name: Any = None
    category: Any = None
    price: Any = None
    packagingCost: Any = None
    available: Any = None
