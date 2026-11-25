from typing import Any

from pydantic import BaseModel


class InventoryItemRequest(BaseModel):
    name: Any = None
    barcode: Any = None
    unit: Any = None
    unitCost: Any = None
    reorderLevel: Any = None


class StockRequest(BaseModel):
    ingredientId: Any = None
    barcode: Any = None
    quantity: Any = None
    batchNo: Any = None
    type: Any = None
    reason: Any = None
