from datetime import date

from src.core.errors import ApiError
from src.core.utils import num, to_money
from src.core.audit import audit
from expenses.models import EXPENSE_TYPES, MAX_AMOUNT
from expenses.repository import add_expense, get_expense, list_expenses


def parse_date(value, field: str):
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        raise ApiError(422, f"{field} must look like 2026-10-28.")


def serialize(row: dict) -> dict:
    return {
        "id": row["expenseid"],
        "date": row["expensedate"].isoformat(),
        "type": row["expensetype"],
        "description": row["description"],
        "amount": num(row["amount"]),
        "recordedBy": row["recordedby"],
    }


def list_expense_response(cur, etype: str | None, date_from: str | None, date_to: str | None, limit: int) -> list[dict]:
    if etype and etype not in EXPENSE_TYPES:
        raise ApiError(422, "Unknown expense type.")
    parsed_from = parse_date(date_from, "date_from") if date_from else None
    parsed_to = parse_date(date_to, "date_to") if date_to else None
    return [serialize(row) for row in list_expenses(cur, etype, parsed_from, parsed_to, limit)]


def add_expense_service(cur, user: dict, body: dict | None) -> tuple[dict, int]:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    etype = str(body.get("type") or "").strip()
    if etype not in EXPENSE_TYPES:
        raise ApiError(422, "Choose a valid expense type.")
    description = str(body.get("description") or "").strip()
    if not description:
        raise ApiError(422, "A description is required.")
    if len(description) > 255:
        raise ApiError(422, "Description is too long (255 characters max).")
    amount = to_money(body.get("amount"))
    if amount <= 0:
        raise ApiError(422, "Amount must be more than zero.")
    if amount > MAX_AMOUNT:
        raise ApiError(422, "Amount is too large.")
    spent_on = parse_date(body["date"], "date") if body.get("date") else date.today()
    expense_id = add_expense(cur, user["userid"], etype, description, amount, spent_on)
    audit(cur, user["userid"], f"Added expense: {etype} ₱{amount}", "EXPENSE", expense_id)
    return serialize(get_expense(cur, expense_id)), 201
