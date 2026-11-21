"""
Expenses API: list and add expenses (the Expense Tracking half of the Expense page).

Uses the same temporary X-Username login as transactions.py. Only the Owner
can see or add expenses, matching the sidebar (Barista has no Expense page).
"""
from datetime import date

from flask import Blueprint, jsonify, request

from transactions import ApiError, audit, handle_api_error, json_body, num, require_owner, to_money, with_db

bp = Blueprint("expenses", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)   # errors raised here need their own handler

# Must match the options in Expense.html
EXPENSE_TYPES = (
    "Rent", "Electricity", "Water", "Internet", "Salaries/Wages", "Supplies",
    "Operating Transportation Expenses", "Maintenance", "Other Expenses",
)
MAX_AMOUNT = 99999999.99   # NUMERIC(10,2)

EXPENSE_SELECT = """
    SELECT e.expenseid, e.expensedate, e.expensetype, e.description, e.amount,
           u.fullname AS recordedby
    FROM expense e
    LEFT JOIN "User" u ON u.userid = e.userid
"""


def serialize(r):
    return {
        "id": r["expenseid"],
        "date": r["expensedate"].isoformat(),
        "type": r["expensetype"],
        "description": r["description"],
        "amount": num(r["amount"]),
        "recordedBy": r["recordedby"],
    }


def parse_date(value, field):
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ApiError(422, f"{field} must look like 2026-10-28.")


@bp.get("/expenses")
@with_db
def list_expenses(cur):
    """Query params (all optional): type, date_from, date_to, limit (default 500, max 1000)."""
    require_owner(cur)
    where, params = [], []

    etype = request.args.get("type")
    if etype:
        if etype not in EXPENSE_TYPES:
            raise ApiError(422, "Unknown expense type.")
        where.append("e.expensetype = %s")
        params.append(etype)

    for key, op in (("date_from", ">="), ("date_to", "<=")):
        value = request.args.get(key)
        if value:
            where.append(f"e.expensedate {op} %s")
            params.append(parse_date(value, key))

    try:
        limit = min(max(int(request.args.get("limit", 500)), 1), 1000)
    except ValueError:
        raise ApiError(422, "limit must be a number.")

    sql = EXPENSE_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY e.expensedate DESC, e.expenseid DESC LIMIT %s"
    cur.execute(sql, params + [limit])
    return jsonify([serialize(r) for r in cur.fetchall()])


@bp.post("/expenses")
@with_db
def add_expense(cur):
    user = require_owner(cur)
    body = json_body()

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

    cur.execute(
        """INSERT INTO expense (userid, expensetype, description, amount, expensedate)
           VALUES (%s, %s, %s, %s, %s) RETURNING expenseid""",
        (user["userid"], etype, description, amount, spent_on),
    )
    expense_id = cur.fetchone()["expenseid"]
    audit(cur, user["userid"], f"Added expense: {etype} ₱{amount}", "EXPENSE", expense_id)

    cur.execute(EXPENSE_SELECT + " WHERE e.expenseid = %s", (expense_id,))
    return jsonify(serialize(cur.fetchone())), 201
