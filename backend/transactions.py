"""
Transactions API: sales list, void, and refund request / approve / reject.

Register in app.py with:
    from transactions import bp as transactions_bp
    app.register_blueprint(transactions_bp)

TEMPORARY LOGIN: there is no real login yet. Every request must send an
"X-Username" header (e.g. "owner" or "barista") and the role comes from the
User table. Anyone can fake this header, so replace current_user() with real
JWT login before deploying.
"""
import re
from decimal import Decimal, InvalidOperation
from functools import wraps

import psycopg2.errors
from flask import Blueprint, jsonify, request
from psycopg2.extras import RealDictCursor

from db import get_conn

bp = Blueprint("transactions", __name__, url_prefix="/api")

# Sales page shows these statuses (Pending / Cancelled POS orders are not transactions).
SALE_STATUSES = ("Completed", "Refunded", "Voided")
WHOLE_ORDER = "Whole order"


# ---------------------------------------------------------------
# Errors and database plumbing
# ---------------------------------------------------------------
class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


@bp.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({"detail": err.message}), err.status


def with_db(fn):
    """Open a connection, pass a dict cursor as the first argument,
    commit on success and roll back on any error."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        conn = get_conn()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            result = fn(cur, *args, **kwargs)
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    return wrapper


# ---------------------------------------------------------------
# Current user (temporary, see module docstring)
# ---------------------------------------------------------------
def current_user(cur):
    username = (request.headers.get("X-Username") or "").strip()
    if not username:
        raise ApiError(401, "Not logged in.")
    cur.execute(
        'SELECT userid, fullname, username, role FROM "User" '
        "WHERE lower(username) = lower(%s) AND isactive",
        (username,),
    )
    user = cur.fetchone()
    if not user:
        raise ApiError(401, "Unknown or inactive user.")
    return user


def require_owner(cur):
    user = current_user(cur)
    if user["role"] != "Owner":
        raise ApiError(403, "Only the Owner can do this.")
    return user


# ---------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------
def to_money(value, field="amount"):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(422, f"{field} must be a number.")
    return amount


def num(value):
    return float(value) if value is not None else 0.0


def iso(dt):
    return dt.isoformat() if dt else None


def audit(cur, user_id, action, table_name, record_id):
    cur.execute(
        "INSERT INTO auditlog (userid, action, tablename, recordid) VALUES (%s, %s, %s, %s)",
        (user_id, action, table_name, record_id),
    )


def json_body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    return body


def serialize_refund(r):
    return {
        "id": r["refundid"],
        "saleId": r["orderid"],
        "item": r["itemname"],
        "amount": num(r["refundamount"]),
        "reason": r["reason"],
        "itemReturned": r["itemreturned"],
        "status": r["status"],
        "requestedBy": r["requestedby"],
        "requestedAt": iso(r["requestedat"]),
        "approvedBy": r["approvedby"],
        "approvedAt": iso(r["approvedat"]),
    }


def serialize_sale(row, refunds):
    items = [
        {"name": i["name"], "qty": i["qty"], "price": float(i["price"]), "customization": i.get("customization")}
        for i in row["items"]
    ]
    subtotal = round(sum(i["qty"] * i["price"] for i in items), 2)
    refunds = [serialize_refund(r) for r in refunds]
    approved = [r for r in refunds if r["status"] == "Approved"]
    pending = [r for r in refunds if r["status"] == "Pending"]
    return {
        "id": row["orderid"],
        "saleNo": f"S{row['orderid']:02d}",
        "orderNo": row["ordernumber"],
        "customer": row["customername"],
        "date": row["orderdatetime"].date().isoformat(),
        "createdAt": iso(row["orderdatetime"]),
        "items": items,
        "subtotal": subtotal,
        "discount": num(row["discountamount"]),
        "serviceCharge": num(row["servicecharge"]),
        "total": num(row["totalamount"]),
        "payment": row["paymentmethod"],
        "status": row["orderstatus"],
        "voidReason": row["voidreason"],
        "voidedBy": row["voidedby"],
        "voidedAt": iso(row["voidedat"]),
        "refunds": refunds,
        "refund": approved[-1] if approved else None,
        "pendingRefund": pending[0] if pending else None,
    }


SALE_SELECT = """
    SELECT o.orderid, o.ordernumber, o.customername, o.orderdatetime, o.discountamount,
           o.servicecharge, o.totalamount, o.paymentmethod, o.orderstatus,
           o.voidreason, o.voidedat, vu.fullname AS voidedby,
           COALESCE((
               SELECT json_agg(json_build_object(
                          'name', oi.itemname, 'qty', oi.quantity,
                          'price', oi.unitprice, 'customization', oi.customization)
                      ORDER BY oi.orderitemid)
               FROM orderitem oi WHERE oi.orderid = o.orderid
           ), '[]'::json) AS items
    FROM orders o
    LEFT JOIN "User" vu ON vu.userid = o.voidedby
"""

REFUND_SELECT = """
    SELECT r.refundid, r.orderid, r.itemname, r.refundamount, r.reason, r.itemreturned,
           r.status, r.requestedat, r.approvedat,
           ru.fullname AS requestedby, au.fullname AS approvedby
    FROM refund r
    LEFT JOIN "User" ru ON ru.userid = r.requestedby
    LEFT JOIN "User" au ON au.userid = r.approvedby
"""


def fetch_refunds(cur, order_ids):
    if not order_ids:
        return {}
    cur.execute(REFUND_SELECT + " WHERE r.orderid = ANY(%s) ORDER BY r.refundid", (list(order_ids),))
    grouped = {}
    for r in cur.fetchall():
        grouped.setdefault(r["orderid"], []).append(r)
    return grouped


def get_sale(cur, order_id):
    cur.execute(SALE_SELECT + " WHERE o.orderid = %s", (order_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "Sale not found.")
    return serialize_sale(row, fetch_refunds(cur, [order_id]).get(order_id, []))


def lock_order(cur, order_id):
    cur.execute(
        "SELECT orderid, orderstatus, totalamount FROM orders WHERE orderid = %s FOR UPDATE",
        (order_id,),
    )
    order = cur.fetchone()
    if not order:
        raise ApiError(404, "Sale not found.")
    return order


def validate_refund_fields(cur, order, item, amount, reason):
    """Checks shared by 'request' and 'approve with edits'."""
    reason = (reason or "").strip()
    item = (item or "").strip()
    if not item:
        raise ApiError(422, "Choose which item is being refunded.")
    if not reason:
        raise ApiError(422, "A refund reason is required.")
    if len(reason) > 255:
        raise ApiError(422, "Reason is too long (255 characters max).")
    if item != WHOLE_ORDER:
        cur.execute("SELECT 1 FROM orderitem WHERE orderid = %s AND itemname = %s", (order["orderid"], item))
        if not cur.fetchone():
            raise ApiError(422, "That item is not part of this sale.")
    if amount <= 0:
        raise ApiError(422, "Refund amount must be more than zero.")
    cur.execute(
        "SELECT COALESCE(SUM(refundamount), 0) AS done FROM refund WHERE orderid = %s AND status = 'Approved'",
        (order["orderid"],),
    )
    available = order["totalamount"] - cur.fetchone()["done"]
    if amount > available:
        raise ApiError(422, f"Refund can't be more than the sale total (₱{available}).")
    return item, reason


# ---------------------------------------------------------------
# Reading sales
# ---------------------------------------------------------------
@bp.get("/transactions")
@with_db
def list_transactions(cur):
    """Query params (all optional):
    tab = sales | discounts | voided | refunded
    payment = Cash | GCash | ...
    q = text to find in order number / sale number
    date_from, date_to = YYYY-MM-DD
    limit = max rows (default 500, max 1000)
    """
    require_owner(cur)
    tab = request.args.get("tab", "sales")
    where, params = [], []

    if tab == "voided":
        where.append("o.orderstatus = 'Voided'")
    elif tab == "refunded":
        where.append("o.orderstatus = 'Refunded'")
    elif tab == "discounts":
        where.append("o.discountamount > 0")
        where.append("o.orderstatus = ANY(%s)")
        params.append(list(SALE_STATUSES))
    elif tab == "sales":
        where.append("o.orderstatus = ANY(%s)")
        params.append(list(SALE_STATUSES))
    else:
        raise ApiError(422, "tab must be sales, discounts, voided or refunded.")

    payment = request.args.get("payment")
    if payment:
        where.append("o.paymentmethod = %s")
        params.append(payment)

    q = (request.args.get("q") or "").strip()
    if q:
        clause = "o.ordernumber ILIKE %s"
        params.append(f"%{q}%")
        m = re.fullmatch(r"[sS]?(\d{1,9})", q)
        if m:
            clause += " OR o.orderid = %s"
            params.append(int(m.group(1)))
        where.append(f"({clause})")

    for key, op in (("date_from", ">="), ("date_to", "<=")):
        value = request.args.get(key)
        if value:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ApiError(422, f"{key} must look like 2026-10-28.")
            where.append(f"o.orderdatetime::date {op} %s")
            params.append(value)

    try:
        limit = min(max(int(request.args.get("limit", 500)), 1), 1000)
    except ValueError:
        raise ApiError(422, "limit must be a number.")

    sql = SALE_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY o.orderdatetime DESC, o.orderid DESC LIMIT %s"
    cur.execute(sql, params + [limit])
    rows = cur.fetchall()
    refunds = fetch_refunds(cur, [r["orderid"] for r in rows])
    return jsonify([serialize_sale(r, refunds.get(r["orderid"], [])) for r in rows])


@bp.get("/transactions/<int:order_id>")
@with_db
def get_transaction(cur, order_id):
    require_owner(cur)
    return jsonify(get_sale(cur, order_id))


@bp.get("/refunds")
@with_db
def list_refunds(cur):
    """Optional ?status=Pending|Approved|Rejected"""
    require_owner(cur)
    status = request.args.get("status")
    sql, params = REFUND_SELECT, []
    if status:
        if status not in ("Pending", "Approved", "Rejected"):
            raise ApiError(422, "status must be Pending, Approved or Rejected.")
        sql += " WHERE r.status = %s"
        params.append(status)
    cur.execute(sql + " ORDER BY r.refundid DESC", params)
    return jsonify([serialize_refund(r) for r in cur.fetchall()])


# ---------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------
@bp.post("/transactions/<int:order_id>/refunds")
@with_db
def request_refund(cur, order_id):
    """Any logged-in user can ask for a refund. It stays Pending until the Owner approves."""
    user = current_user(cur)
    body = json_body()
    amount = to_money(body.get("amount"))

    order = lock_order(cur, order_id)
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be refunded (this one is {order['orderstatus']}).")
    item, reason = validate_refund_fields(cur, order, body.get("item"), amount, body.get("reason"))

    try:
        cur.execute(
            """INSERT INTO refund (orderid, refundamount, reason, itemreturned, status, requestedby, itemname)
               VALUES (%s, %s, %s, %s, 'Pending', %s, %s) RETURNING refundid""",
            (order_id, amount, reason, bool(body.get("itemReturned")), user["userid"], item),
        )
    except psycopg2.errors.UniqueViolation:
        raise ApiError(409, "This sale already has a pending refund request.")
    refund_id = cur.fetchone()["refundid"]
    audit(cur, user["userid"], f"Requested refund for S{order_id:02d}", "REFUND", refund_id)
    return jsonify(get_sale(cur, order_id)), 201


def load_pending_refund(cur, refund_id):
    cur.execute("SELECT orderid FROM refund WHERE refundid = %s", (refund_id,))
    first = cur.fetchone()
    if not first:
        raise ApiError(404, "Refund not found.")
    order = lock_order(cur, first["orderid"])          # lock the sale first, then the refund
    cur.execute("SELECT * FROM refund WHERE refundid = %s FOR UPDATE", (refund_id,))
    refund = cur.fetchone()
    if refund["status"] != "Pending":
        raise ApiError(409, f"This refund is already {refund['status']}.")
    return order, refund


@bp.post("/refunds/<int:refund_id>/approve")
@with_db
def approve_refund(cur, refund_id):
    """Owner only. The body is optional; send item / amount / reason / itemReturned to edit before approving."""
    user = require_owner(cur)
    body = request.get_json(silent=True) or {}
    order, refund = load_pending_refund(cur, refund_id)
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be refunded (this one is {order['orderstatus']}).")

    item = body.get("item", refund["itemname"])
    reason = body.get("reason", refund["reason"])
    amount = to_money(body["amount"]) if "amount" in body else refund["refundamount"]
    returned = bool(body["itemReturned"]) if "itemReturned" in body else refund["itemreturned"]
    item, reason = validate_refund_fields(cur, order, item, amount, reason)

    cur.execute(
        """UPDATE refund SET status = 'Approved', approvedby = %s, approvedat = CURRENT_TIMESTAMP,
                  itemname = %s, refundamount = %s, reason = %s, itemreturned = %s
           WHERE refundid = %s""",
        (user["userid"], item, amount, reason, returned, refund_id),
    )
    cur.execute("UPDATE orders SET orderstatus = 'Refunded' WHERE orderid = %s", (order["orderid"],))
    audit(cur, user["userid"], f"Approved refund for S{order['orderid']:02d}", "REFUND", refund_id)

    return jsonify({
        "sale": get_sale(cur, order["orderid"]),
        # the frontend uses this to update stock: restore if the item came back, otherwise record waste
        "inventory": {"action": "restore" if returned else "waste", "item": item},
    })


@bp.post("/refunds/<int:refund_id>/reject")
@with_db
def reject_refund(cur, refund_id):
    user = require_owner(cur)
    order, refund = load_pending_refund(cur, refund_id)
    cur.execute("UPDATE refund SET status = 'Rejected' WHERE refundid = %s", (refund_id,))
    audit(cur, user["userid"], f"Rejected refund for S{order['orderid']:02d}", "REFUND", refund_id)
    return jsonify(get_sale(cur, order["orderid"]))


# ---------------------------------------------------------------
# Void
# ---------------------------------------------------------------
@bp.post("/transactions/<int:order_id>/void")
@with_db
def void_sale(cur, order_id):
    user = require_owner(cur)
    reason = str(json_body().get("reason") or "").strip()
    if not reason:
        raise ApiError(422, "A void reason is required.")
    if len(reason) > 255:
        raise ApiError(422, "Reason is too long (255 characters max).")

    order = lock_order(cur, order_id)
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be voided (this one is {order['orderstatus']}).")

    cur.execute(
        """UPDATE orders SET orderstatus = 'Voided', voidreason = %s, voidedby = %s, voidedat = CURRENT_TIMESTAMP
           WHERE orderid = %s""",
        (reason, user["userid"], order_id),
    )
    # a pending refund request no longer makes sense once the sale is voided
    cur.execute("UPDATE refund SET status = 'Rejected' WHERE orderid = %s AND status = 'Pending'", (order_id,))
    audit(cur, user["userid"], f"Voided sale S{order_id:02d}", "SALE", order_id)

    return jsonify({"sale": get_sale(cur, order_id), "inventory": {"action": "restore", "item": WHOLE_ORDER}})
