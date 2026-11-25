from decimal import Decimal, InvalidOperation
from typing import Any

from src.core.errors import ApiError


def to_money(value: Any, field: str = "amount") -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(422, f"{field} must be a number.")
    return amount


def num(value: Any) -> float:
    return float(value) if value is not None else 0.0


def iso(value: Any) -> str | None:
    return value.isoformat() if value else None
