"""
Inventory API: ingredients, FIFO stock batches and the movement log.
pos.py uses recipe_needs, consume_stock and restore_stock when orders change.
"""
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify
from transactions import (ApiError, audit, current_user, handle_api_error, iso,
                          json_body, num, require_owner, to_money, with_db)

bp = Blueprint("inventory", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)

ZERO = Decimal("0")

INGREDIENT_SQL = """
    SELECT i.ingredientid, i.name, i.barcode, i.unit, i.unitcost,
           i.beginningstock, i.reorderlevel,
           COALESCE((SELECT SUM(b.qtyremaining) FROM stockbatch b
                     WHERE b.ingredientid = i.ingredientid), 0) AS remaining,
           COALESCE((SELECT SUM(m.quantity) FROM stockmovement m
                     WHERE m.ingredientid = i.ingredientid
                       AND m.movementtype = 'Stock-In'), 0) AS stock_in,
           COALESCE((SELECT SUM(CASE WHEN m.movementtype IN ('Stock-Out', 'Waste') THEN m.quantity
                                     WHEN m.movementtype = 'Restore' THEN -m.quantity
                                     ELSE 0 END)
                     FROM stockmovement m
                     WHERE m.ingredientid = i.ingredientid), 0) AS stock_out,
           (SELECT b.batchno FROM stockbatch b
             WHERE b.ingredientid = i.ingredientid AND b.qtyremaining > 0
             ORDER BY b.receiveddate, b.batchid LIMIT 1) AS oldest_batch
    FROM ingredient i
    WHERE i.isactive
    ORDER BY i.name
"""


def status_of(remaining, reorder):
    if remaining <= 0:
        return "Out-of-Stock"
    if remaining <= reorder:
        return "Low-Stock"
    return "Available"


def positive_qty(value):
    try:
        qty = Decimal(str(value))
    except InvalidOperation:
        raise ApiError(422, "Quantity must be a number.")
    if qty <= ZERO:
        raise ApiError(422, "Quantity must be more than zero.")
    return qty


def find_ingredient(cur, body):
    if body.get("ingredientId") not in (None, ""):
        try:
            key = int(body["ingredientId"])
        except (TypeError, ValueError):
            raise ApiError(422, "ingredientId must be a number.")
        cur.execute("SELECT ingredientid FROM ingredient WHERE ingredientid = %s", (key,))
    elif body.get("barcode"):
        cur.execute("SELECT ingredientid FROM ingredient WHERE barcode = %s", (str(body["barcode"]),))
    else:
        raise ApiError(422, "Choose an ingredient.")
    row = cur.fetchone()
    if not row:
        raise ApiError(404, "Ingredient not found.")
    return row["ingredientid"]


def recipe_needs(cur, product_qtys):
    """product_qtys: list of (productid, qty). Returns {ingredientid: Decimal}."""
    needs = {}
    for product_id, qty in product_qtys:
        cur.execute("SELECT ingredientid, qtyused FROM recipe WHERE productid = %s", (product_id,))
        for r in cur.fetchall():
            needs[r["ingredientid"]] = needs.get(r["ingredientid"], ZERO) + r["qtyused"] * qty
    return needs


def take_from_batches(cur, ingredient_id, qty, user_id, movement_type, order_id=None, note=None):
    """Take qty from the oldest batches first (FIFO) and log each batch touched."""
    cur.execute("SELECT name FROM ingredient WHERE ingredientid = %s FOR UPDATE", (ingredient_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiError(404, "Ingredient not found.")
    cur.execute(
        "SELECT batchid, qtyremaining FROM stockbatch "
        "WHERE ingredientid = %s AND qtyremaining > 0 "
        "ORDER BY receiveddate, batchid FOR UPDATE",
        (ingredient_id,),
    )
    batches = cur.fetchall()
    if sum((b["qtyremaining"] for b in batches), ZERO) < qty:
        raise ApiError(409, f"Not enough {row['name']} in stock.")

    left = qty
    for b in batches:
        if left <= 0:
            break
        take = min(b["qtyremaining"], left)
        cur.execute("UPDATE stockbatch SET qtyremaining = qtyremaining - %s WHERE batchid = %s",
                    (take, b["batchid"]))
        cur.execute(
            "INSERT INTO stockmovement (ingredientid, batchid, orderid, userid, movementtype, quantity, note) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (ingredient_id, b["batchid"], order_id, user_id, movement_type, take, note),
        )
        left -= take


def consume_stock(cur, needs, user_id, order_id):
    for ingredient_id, qty in needs.items():
        take_from_batches(cur, ingredient_id, qty, user_id, "Stock-Out", order_id)


def restore_stock(cur, order_id, user_id):
    """Put back the net amount taken for this order (taken minus already restored)."""
    cur.execute(
        "SELECT ingredientid, SUM(CASE WHEN movementtype = 'Stock-Out' THEN quantity "
        "                              WHEN movementtype = 'Restore' THEN -quantity "
        "                              ELSE 0 END) AS net "
        "FROM stockmovement WHERE orderid = %s GROUP BY ingredientid",
        (order_id,),
    )
    for row in cur.fetchall():
        net = row["net"]
        if net and net > 0:
            cur.execute(
                "INSERT INTO stockbatch (ingredientid, batchno, qtyreceived, qtyremaining) "
                "VALUES (%s, %s, %s, %s) RETURNING batchid",
                (row["ingredientid"], f"RST-{order_id}", net, net),
            )
            batch_id = cur.fetchone()["batchid"]
            cur.execute(
                "INSERT INTO stockmovement (ingredientid, batchid, orderid, userid, movementtype, quantity, note) "
                "VALUES (%s, %s, %s, %s, 'Restore', %s, 'Order cancelled')",
                (row["ingredientid"], batch_id, order_id, user_id, net),
            )


@bp.get("/inventory")
@with_db
def list_inventory(cur):
    current_user(cur)
    cur.execute(INGREDIENT_SQL)
    rows = []
    for r in cur.fetchall():
        rows.append({
            "id": r["ingredientid"],
            "name": r["name"],
            "barcode": r["barcode"],
            "unit": r["unit"],
            "unitCost": num(r["unitcost"]),
            "beginning": num(r["beginningstock"]),
            "stockIn": num(r["stock_in"]),
            "stockOut": num(r["stock_out"]),
            "remaining": num(r["remaining"]),
            "reorderLevel": num(r["reorderlevel"]),
            "batchNo": r["oldest_batch"] or "—",
            "status": status_of(r["remaining"], r["reorderlevel"]),
        })
    return jsonify(rows)


@bp.get("/inventory/movements")
@with_db
def list_movements(cur):
    current_user(cur)
    cur.execute("""
        SELECT m.movementid, m.createdat, i.name, m.movementtype, m.quantity,
               b.batchno, u.fullname AS by_user, m.orderid
        FROM stockmovement m
        JOIN ingredient i ON i.ingredientid = m.ingredientid
        LEFT JOIN stockbatch b ON b.batchid = m.batchid
        LEFT JOIN "User" u ON u.userid = m.userid
        ORDER BY m.createdat DESC, m.movementid DESC
        LIMIT 50
    """)
    return jsonify([{
        "id": r["movementid"], "date": iso(r["createdat"]), "item": r["name"],
        "type": r["movementtype"], "qty": num(r["quantity"]),
        "batchNo": r["batchno"], "by": r["by_user"], "orderId": r["orderid"],
    } for r in cur.fetchall()])


@bp.post("/inventory/items")
@with_db
def add_item(cur):
    require_owner(cur)
    body = json_body()
    name = str(body.get("name") or "").strip()
    unit = str(body.get("unit") or "").strip()
    if not name or not unit:
        raise ApiError(422, "Enter a name and a unit.")
    cur.execute("SELECT 1 FROM ingredient WHERE lower(name) = lower(%s)", (name,))
    if cur.fetchone():
        raise ApiError(409, "That item already exists.")
    barcode = str(body.get("barcode") or "").strip() or None
    unit_cost = to_money(body.get("unitCost") or 0, "unit cost")
    reorder = to_money(body.get("reorderLevel") or 0, "reorder level")
    cur.execute(
        "INSERT INTO ingredient (name, barcode, unit, unitcost, reorderlevel) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING ingredientid",
        (name[:60], barcode, unit[:20], unit_cost, reorder),
    )
    return jsonify({"id": cur.fetchone()["ingredientid"]}), 201


@bp.post("/inventory/stock-in")
@with_db
def stock_in(cur):
    user = current_user(cur)
    body = json_body()
    ingredient_id = find_ingredient(cur, body)
    qty = positive_qty(body.get("quantity"))
    batch_no = str(body.get("batchNo") or "").strip()[:45]
    if not batch_no:
        raise ApiError(422, "Enter a batch number.")
    cur.execute(
        "INSERT INTO stockbatch (ingredientid, batchno, qtyreceived, qtyremaining) "
        "VALUES (%s, %s, %s, %s) RETURNING batchid",
        (ingredient_id, batch_no, qty, qty),
    )
    batch_id = cur.fetchone()["batchid"]
    cur.execute(
        "INSERT INTO stockmovement (ingredientid, batchid, userid, movementtype, quantity) "
        "VALUES (%s, %s, %s, 'Stock-In', %s)",
        (ingredient_id, batch_id, user["userid"], qty),
    )
    return jsonify({"ok": True, "batchId": batch_id})


@bp.post("/inventory/stock-out")
@with_db
def stock_out(cur):
    """Manual use or waste. Waste needs a reason."""
    user = current_user(cur)
    body = json_body()
    ingredient_id = find_ingredient(cur, body)
    qty = positive_qty(body.get("quantity"))
    kind = body.get("type") or "Stock-Out"
    if kind not in ("Stock-Out", "Waste"):
        raise ApiError(422, "Type must be Stock-Out or Waste.")
    note = str(body.get("reason") or "").strip() or None
    if kind == "Waste" and not note:
        raise ApiError(422, "Enter a reason for the waste.")
    take_from_batches(cur, ingredient_id, qty, user["userid"], kind, None, note)
    return jsonify({"ok": True})