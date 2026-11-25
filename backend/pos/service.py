from decimal import Decimal, InvalidOperation

from src.core.errors import ApiError
from src.core.utils import iso, num, to_money
from src.core.audit import audit
from inventory.service import consume_stock, recipe_needs, restore_stock
from pos.models import STATUSES
from pos.repository import (
    add_order_item,
    create_order,
    find_available_product,
    get_order,
    list_order_items,
    list_orders,
    lock_order_status,
    next_order_number,
    order_recipe_rows,
    set_order_status,
)


ZERO = Decimal("0")


def describe(item: dict) -> str | None:
    parts = [
        item.get("size"),
        item.get("shots"),
        f"Sweetness {item['sweetness']}" if item.get("sweetness") else None,
        item.get("ice"),
        f"Notes: {item['notes']}" if item.get("notes") else None,
    ]
    return " · ".join(str(part) for part in parts if part) or None


def order_row(row: dict) -> dict:
    return {
        "id": row["orderid"],
        "orderNumber": row["ordernumber"],
        "customer": row["customername"],
        "total": num(row["totalamount"]),
        "status": row["orderstatus"],
        "createdAt": iso(row["orderdatetime"]),
    }


def list_order_response(cur) -> list[dict]:
    return [order_row(row) for row in list_orders(cur)]


def get_order_response(cur, order_id: int) -> dict:
    row = get_order(cur, order_id)
    if not row:
        raise ApiError(404, "Order not found.")
    items = [{
        "name": item["itemname"],
        "qty": item["quantity"],
        "price": num(item["unitprice"]),
        "customization": item["customization"],
    } for item in list_order_items(cur, order_id)]
    return {
        **order_row(row),
        "discount": num(row["discountamount"]),
        "payment": row["paymentmethod"],
        "tendered": num(row["amounttendered"]),
        "cancelReason": row["cancelreason"],
        "items": items,
    }


def create_order_service(cur, user: dict, body: dict | None) -> tuple[dict, int]:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    raw_items = body.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ApiError(422, "Add at least one item.")
    lines, subtotal = [], ZERO
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ApiError(422, "Each item must be an object.")
        try:
            product_id = int(raw["productId"])
            qty = int(raw["qty"])
        except (KeyError, TypeError, ValueError):
            raise ApiError(422, "Each item needs productId and qty.")
        if not 1 <= qty <= 99:
            raise ApiError(422, "Quantity must be between 1 and 99.")
        price = to_money(raw.get("price"), "price")
        product = find_available_product(cur, product_id)
        if not product:
            raise ApiError(422, "One of the products is not available.")
        subtotal += price * qty
        lines.append((product_id, product["productname"], qty, price, describe(raw)))

    try:
        pct = Decimal(str(body.get("discountPercent") or 0))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(422, "Discount must be a number.")
    pct = min(max(pct, ZERO), Decimal("100"))
    discount = (subtotal * pct / 100).quantize(Decimal("0.01"))
    total = subtotal - discount
    payment = str(body.get("payment") or "Cash")
    if payment == "Cash":
        tendered = to_money(body.get("tendered") or 0, "tendered")
        if tendered < total:
            raise ApiError(422, f"Amount tendered is short by ₱{total - tendered:,.2f}.")
    else:
        tendered = total
    change = tendered - total
    customer = str(body.get("customer") or "").strip()[:45] or "Walk-in"
    order_number = next_order_number(cur)
    order_id = create_order(cur, user["userid"], order_number, customer, total, discount, payment, tendered)
    for product_id, name, qty, price, customization in lines:
        add_order_item(cur, order_id, product_id, name, qty, price, customization)
    needs = recipe_needs(cur, [(pid, qty) for pid, _, qty, _, _ in lines])
    consume_stock(cur, needs, user["userid"], order_id)
    audit(cur, user["userid"], f"Created order {order_number}", "orders", order_id)
    return {
        "id": order_id,
        "orderNumber": order_number,
        "total": num(total),
        "change": num(change),
    }, 201


def set_status_service(cur, user: dict, order_id: int, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    status = body.get("status")
    if status not in STATUSES:
        raise ApiError(422, "Status must be Pending, Completed or Cancelled.")
    row = lock_order_status(cur, order_id)
    if not row:
        raise ApiError(404, "Order not found.")
    current = row["orderstatus"]
    if current in ("Voided", "Refunded"):
        raise ApiError(409, "Voided or refunded orders can't change here. Use Transactions.")
    if status == current:
        return {"ok": True}
    if status == "Cancelled":
        reason = str(body.get("reason") or "").strip()
        if not reason:
            raise ApiError(422, "Enter a reason for cancelling.")
        restore_stock(cur, order_id, user["userid"])
        set_order_status(cur, order_id, "Cancelled", reason[:255])
    else:
        if current == "Cancelled":
            needs = recipe_needs(
                cur,
                [(item["productid"], item["quantity"]) for item in order_recipe_rows(cur, order_id)],
            )
            consume_stock(cur, needs, user["userid"], order_id)
        set_order_status(cur, order_id, status)
    audit(cur, user["userid"], f"Order {order_id} status set to {status}", "orders", order_id)
    return {"ok": True}
