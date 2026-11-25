from decimal import Decimal
from typing import TypedDict


ZERO = Decimal("0")


class IngredientRow(TypedDict, total=False):
    ingredientid: int
    name: str
    barcode: str | None
    unit: str
    unitcost: Decimal
    beginningstock: Decimal
    reorderlevel: Decimal
