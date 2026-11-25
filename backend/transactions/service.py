import re

import psycopg2.errors

from src.core.errors import ApiError
from src.core.utils import iso, num, to_money
from src.core.audit import audit
from transactions.models import SALE_STATUSES, WHOLE_ORDER
from transactions.repository import (
    create_refund,
    fetch_refunds,
    fetch_sales,
    find_pending_refund,
    get_sale_row,
    list_refunds,
    lock_order,
    lock_refund,
    refund_item_exists,
    refund_total_for_order,
    reject_pending_refunds,
    reject_refund,
    set_order_refunded,
    update_refund,
    void_order,
)


def serialize_refund(row: dict) -> dict:
    return {
        "id": row["refundid"],
        "saleId": row["orderid"],
        "item": row["itemname"],
        "amount": num(row["refundamount"]),
        "reason": row["reason"],
        "itemReturned": row["itemreturned"],
        "status": row["status"],
        "requestedBy": row["requestedby"],
        "requestedAt": iso(row["requestedat"]),
        "approvedBy": row["approvedby"],
        "approvedAt": iso(row["approvedat"]),
    }


def serialize_sale(row: dict, refunds: list[dict]) -> dict:
    items = [
        {"name": item["name"], "qty": item["qty"], "price": float(item["price"]),
         "customization": item.get("customization")}
        for item in row["items"]
    ]
    subtotal = round(sum(item["qty"] * item["price"] for item in items), 2)
    serialized_refunds = [serialize_refund(refund) for refund in refunds]
    approved = [refund for refund in serialized_refunds if refund["status"] == "Approved"]
    pending = [refund for refund in serialized_refunds if refund["status"] == "Pending"]
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
        "discountNote": row.get("discountnote") or "",
        "serviceCharge": num(row["servicecharge"]),
        "total": num(row["totalamount"]),
        "payment": row["paymentmethod"],
        "status": row["orderstatus"],
        "voidReason": row["voidreason"],
        "voidedBy": row["voidedby"],
        "voidedAt": iso(row["voidedat"]),
        "refunds": serialized_refunds,
        "refund": approved[-1] if approved else None,
        "pendingRefund": pending[0] if pending else None,
    }


def get_sale(cur, order_id: int) -> dict:
    row = get_sale_row(cur, order_id)
    if not row:
        raise ApiError(404, "Sale not found.")
    refunds = fetch_refunds(cur, [order_id]).get(order_id, [])
    return serialize_sale(row, refunds)


def list_sales(cur, tab: str, payment: str | None, query: str | None,
               date_from: str | None, date_to: str | None, limit: int) -> list[dict]:
    valid_tabs = ("sales", "discounts", "voided", "refunded")
    if tab not in valid_tabs:
        raise ApiError(422, "tab must be sales, discounts, voided or refunded.")
    for value, field in ((date_from, "date_from"), (date_to, "date_to")):
        if value and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ApiError(422, f"{field} must look like 2026-10-28.")
    rows = fetch_sales(cur, tab, payment, (query or "").strip() or None,
                       date_from, date_to, limit)
    refunds = fetch_refunds(cur, [row["orderid"] for row in rows])
    return [serialize_sale(row, refunds.get(row["orderid"], [])) for row in rows]


def list_refund_response(cur, status: str | None) -> list[dict]:
    if status and status not in ("Pending", "Approved", "Rejected"):
        raise ApiError(422, "status must be Pending, Approved or Rejected.")
    return [serialize_refund(row) for row in list_refunds(cur, status)]


def validate_refund_fields(cur, order: dict, item, amount, reason):
    reason = (reason or "").strip()
    item = (item or "").strip()
    if not item:
        raise ApiError(422, "Choose which item is being refunded.")
    if not reason:
        raise ApiError(422, "A refund reason is required.")
    if len(reason) > 255:
        raise ApiError(422, "Reason is too long (255 characters max).")
    if item != WHOLE_ORDER and not refund_item_exists(cur, order["orderid"], item):
        raise ApiError(422, "That item is not part of this sale.")
    if amount <= 0:
        raise ApiError(422, "Refund amount must be more than zero.")
    available = order["totalamount"] - refund_total_for_order(cur, order["orderid"])
    if amount > available:
        raise ApiError(422, f"Refund can't be more than the sale total (₱{available}).")
    return item, reason


def request_refund(cur, user: dict, order_id: int, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    amount = to_money(body.get("amount"))
    order = lock_order(cur, order_id)
    if not order:
        raise ApiError(404, "Sale not found.")
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be refunded (this one is {order['orderstatus']}).")
    item, reason = validate_refund_fields(cur, order, body.get("item"), amount, body.get("reason"))
    try:
        refund_id = create_refund(
            cur, order_id, amount, reason, item,
            bool(body.get("itemReturned")), user["userid"],
        )
    except psycopg2.errors.UniqueViolation:
        raise ApiError(409, "This sale already has a pending refund request.")
    audit(cur, user["userid"], f"Requested refund for S{order_id:02d}", "REFUND", refund_id)
    return get_sale(cur, order_id)


def load_pending_refund(cur, refund_id: int):
    first = find_pending_refund(cur, refund_id)
    if not first:
        raise ApiError(404, "Refund not found.")
    order = lock_order(cur, first["orderid"])
    refund = lock_refund(cur, refund_id)
    if refund["status"] != "Pending":
        raise ApiError(409, f"This refund is already {refund['status']}.")
    return order, refund


def approve_refund(cur, user: dict, refund_id: int, body: dict | None) -> dict:
    body = body if isinstance(body, dict) else {}
    order, refund = load_pending_refund(cur, refund_id)
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be refunded (this one is {order['orderstatus']}).")
    item = body.get("item", refund["itemname"])
    reason = body.get("reason", refund["reason"])
    amount = to_money(body["amount"]) if "amount" in body else refund["refundamount"]
    returned = bool(body["itemReturned"]) if "itemReturned" in body else refund["itemreturned"]
    item, reason = validate_refund_fields(cur, order, item, amount, reason)
    update_refund(cur, refund_id, user["userid"], item, amount, reason, returned)
    set_order_refunded(cur, order["orderid"])
    audit(cur, user["userid"], f"Approved refund for S{order['orderid']:02d}", "REFUND", refund_id)
    return {
        "sale": get_sale(cur, order["orderid"]),
        "inventory": {"action": "restore" if returned else "waste", "item": item},
    }


def reject_refund_service(cur, user: dict, refund_id: int) -> dict:
    order, _refund = load_pending_refund(cur, refund_id)
    reject_refund(cur, refund_id)
    audit(cur, user["userid"], f"Rejected refund for S{order['orderid']:02d}", "REFUND", refund_id)
    return get_sale(cur, order["orderid"])


def void_sale(cur, user: dict, order_id: int, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    reason = str(body.get("reason") or "").strip()
    if not reason:
        raise ApiError(422, "A void reason is required.")
    if len(reason) > 255:
        raise ApiError(422, "Reason is too long (255 characters max).")
    order = lock_order(cur, order_id)
    if not order:
        raise ApiError(404, "Sale not found.")
    if order["orderstatus"] != "Completed":
        raise ApiError(409, f"Only Completed sales can be voided (this one is {order['orderstatus']}).")
    void_order(cur, order_id, reason, user["userid"])
    reject_pending_refunds(cur, order_id)
    audit(cur, user["userid"], f"Voided sale S{order_id:02d}", "SALE", order_id)
    return {
        "sale": get_sale(cur, order_id),
        "inventory": {"action": "restore", "item": WHOLE_ORDER},
    }
