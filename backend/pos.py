"""
POS API: menu products, placing orders, and changing order status.
Placing an order deducts ingredients from recipes. Cancelling restores them,
and reopening deducts again.
"""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify
from transactions import (ApiError, audit, current_user, handle_api_error,
                          iso, json_body, num, to_money, with_db)
from inventory import consume_stock, recipe_needs, restore_stock

bp = Blueprint("pos", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)

ZERO = Decimal("0")
STATUSES = ("Pending", "Completed", "Cancelled")
ORDER_COLUMNS = ("orderid, ordernumber, customername, totalamount, discountamount, "
                 "paymentmethod, amounttendered, orderstatus, orderdatetime, cancelreason")


def describe(item):
    parts = [
        item.get("size"),
        item.get("shots"),
        f"Sweetness {item['sweetness']}" if item.get("sweetness") else None,
        item.get("ice"),
        f"Notes: {item['notes']}" if item.get("notes") else None,
    ]
    return " · ".join(str(p) for p in parts if p) or None


def order_row(o):
    return {
        "id": o["orderid"],
        "orderNumber": o["ordernumber"],
        "customer": o["customername"],
        "total": num(o["totalamount"]),
        "status": o["orderstatus"],
        "createdAt": iso(o["orderdatetime"]),
    }


def order_needs(cur, order_id):
    cur.execute("SELECT productid, quantity FROM orderitem "
                "WHERE orderid = %s AND productid IS NOT NULL", (order_id,))
    return recipe_needs(cur, [(r["productid"], r["quantity"]) for r in cur.fetchall()])


@bp.get("/products")
@with_db
def list_products(cur):
    cur.execute("SELECT productid, productname, category, sellingprice "
                "FROM product WHERE isavailable ORDER BY category, productname")
    return jsonify([{
        "id": r["productid"],
        "name": r["productname"],
        "category": r["category"],
        "price": num(r["sellingprice"]),
    } for r in cur.fetchall()])


@bp.post("/orders")
@with_db
def create_order(cur):
    user = current_user(cur)
    body = json_body()
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
        cur.execute("SELECT productname FROM product WHERE productid = %s AND isavailable",
                    (product_id,))
        product = cur.fetchone()
        if not product:
            raise ApiError(422, "One of the products is not available.")
        subtotal += price * qty
        lines.append((product_id, product["productname"], qty, price, describe(raw)))

    try:
        pct = Decimal(str(body.get("discountPercent") or 0))
    except InvalidOperation:
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
    cur.execute("SELECT COALESCE(MAX(CASE WHEN ordernumber ~ '^[0-9]+$'"
                " THEN CAST(ordernumber AS INT) END), 0) + 1 AS n FROM orders")
    order_no = f"{cur.fetchone()['n']:03d}"

    cur.execute(
        "INSERT INTO orders (userid, ordernumber, customername, totalamount, discountamount, "
        "paymentmethod, amounttendered, orderstatus) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'Completed') RETURNING orderid",
        (user["userid"], order_no, customer, total, discount, payment, tendered),
    )
    order_id = cur.fetchone()["orderid"]

    for product_id, name, qty, price, custom in lines:
        cur.execute(
            "INSERT INTO orderitem (orderid, productid, itemname, quantity, unitprice, customization) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (order_id, product_id, name, qty, price, custom),
        )

    needs = recipe_needs(cur, [(pid, qty) for pid, _, qty, _, _ in lines])
    consume_stock(cur, needs, user["userid"], order_id)

    audit(cur, user["userid"], f"Created order {order_no}", "orders", order_id)
    return jsonify({
        "id": order_id,
        "orderNumber": order_no,
        "total": num(total),
        "change": num(change),
    }), 201


@bp.get("/orders")
@with_db
def list_orders(cur):
    current_user(cur)
    cur.execute(f"SELECT {ORDER_COLUMNS} FROM orders "
                "WHERE orderdatetime::date = CURRENT_DATE ORDER BY orderdatetime DESC")
    return jsonify([order_row(r) for r in cur.fetchall()])


@bp.get("/orders/<int:order_id>")
@with_db
def get_order(cur, order_id):
    current_user(cur)
    cur.execute(f"SELECT {ORDER_COLUMNS} FROM orders WHERE orderid = %s", (order_id,))
    o = cur.fetchone()
    if not o:
        raise ApiError(404, "Order not found.")
    cur.execute("SELECT itemname, quantity, unitprice, customization FROM orderitem "
                "WHERE orderid = %s ORDER BY orderitemid", (order_id,))
    items = [{"name": r["itemname"], "qty": r["quantity"], "price": num(r["unitprice"]),
              "customization": r["customization"]} for r in cur.fetchall()]
    return jsonify({
        **order_row(o),
        "discount": num(o["discountamount"]),
        "payment": o["paymentmethod"],
        "tendered": num(o["amounttendered"]),
        "cancelReason": o["cancelreason"],
        "items": items,
    })


@bp.patch("/orders/<int:order_id>/status")
@with_db
def set_status(cur, order_id):
    user = current_user(cur)
    body = json_body()
    status = body.get("status")
    if status not in STATUSES:
        raise ApiError(422, "Status must be Pending, Completed or Cancelled.")

    cur.execute("SELECT orderstatus FROM orders WHERE orderid = %s FOR UPDATE", (order_id,))
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "Order not found.")
    current = row["orderstatus"]
    if current in ("Voided", "Refunded"):
        raise ApiError(409, "Voided or refunded orders can't change here. Use Transactions.")
    if status == current:
        return jsonify({"ok": True})

    if status == "Cancelled":
        reason = str(body.get("reason") or "").strip()
        if not reason:
            raise ApiError(422, "Enter a reason for cancelling.")
        restore_stock(cur, order_id, user["userid"])
        cur.execute("UPDATE orders SET orderstatus = 'Cancelled', cancelreason = %s "
                    "WHERE orderid = %s", (reason[:255], order_id))
    else:
        if current == "Cancelled":
            consume_stock(cur, order_needs(cur, order_id), user["userid"], order_id)
        cur.execute("UPDATE orders SET orderstatus = %s, cancelreason = NULL "
                    "WHERE orderid = %s", (status, order_id))

    audit(cur, user["userid"], f"Order {order_id} status set to {status}", "orders", order_id)
    return jsonify({"ok": True})