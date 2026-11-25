from decimal import Decimal, InvalidOperation

from src.core.errors import ApiError
from src.core.utils import iso, num, to_money
from inventory.models import ZERO
from inventory.repository import (
    add_ingredient,
    add_stock_movement,
    consume_batch,
    create_stock_batch,
    find_ingredient,
    ingredient_name_exists,
    list_fifo_batches,
    list_inventory,
    list_movements,
    lock_ingredient,
    recipe_rows,
    stock_movement_net,
)


def status_of(remaining, reorder):
    if remaining <= 0:
        return "Out-of-Stock"
    if remaining <= reorder:
        return "Low-Stock"
    return "Available"


def positive_qty(value):
    try:
        qty = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ApiError(422, "Quantity must be a number.")
    if qty <= ZERO:
        raise ApiError(422, "Quantity must be more than zero.")
    return qty


def find_ingredient_service(cur, body: dict) -> int:
    if body.get("ingredientId") not in (None, ""):
        try:
            ingredient_id = int(body["ingredientId"])
        except (TypeError, ValueError):
            raise ApiError(422, "ingredientId must be a number.")
        row = find_ingredient(cur, ingredient_id=ingredient_id)
    elif body.get("barcode"):
        row = find_ingredient(cur, barcode=str(body["barcode"]))
    else:
        raise ApiError(422, "Choose an ingredient.")
    if not row:
        raise ApiError(404, "Ingredient not found.")
    return row["ingredientid"]


def list_inventory_response(cur) -> list[dict]:
    rows = []
    for row in list_inventory(cur):
        remaining = row["remaining"]
        rows.append({
            "id": row["ingredientid"],
            "name": row["name"],
            "barcode": row["barcode"],
            "unit": row["unit"],
            "unitCost": num(row["unitcost"]),
            "beginning": num(row["beginningstock"]),
            "stockIn": num(row["stock_in"]),
            "stockOut": num(row["stock_out"]),
            "remaining": num(remaining),
            "reorderLevel": num(row["reorderlevel"]),
            "batchNo": row["oldest_batch"] or "—",
            "status": status_of(remaining, row["reorderlevel"]),
        })
    return rows


def list_movement_response(cur) -> list[dict]:
    return [{
        "id": r["movementid"], "date": iso(r["createdat"]), "item": r["name"],
        "type": r["movementtype"], "qty": num(r["quantity"]),
        "batchNo": r["batchno"], "by": r["by_user"], "orderId": r["orderid"],
    } for r in list_movements(cur)]


def add_item_service(cur, body: dict | None) -> tuple[dict, int]:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    name = str(body.get("name") or "").strip()
    unit = str(body.get("unit") or "").strip()
    if not name or not unit:
        raise ApiError(422, "Enter a name and a unit.")
    if ingredient_name_exists(cur, name):
        raise ApiError(409, "That item already exists.")
    barcode = str(body.get("barcode") or "").strip() or None
    unit_cost = to_money(body.get("unitCost") or 0, "unit cost")
    reorder = to_money(body.get("reorderLevel") or 0, "reorder level")
    ingredient_id = add_ingredient(cur, name, barcode, unit, unit_cost, reorder)
    return {"id": ingredient_id}, 201


def stock_in_service(cur, user: dict, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    ingredient_id = find_ingredient_service(cur, body)
    qty = positive_qty(body.get("quantity"))
    batch_no = str(body.get("batchNo") or "").strip()[:45]
    if not batch_no:
        raise ApiError(422, "Enter a batch number.")
    batch_id = create_stock_batch(cur, ingredient_id, batch_no, qty)
    add_stock_movement(cur, ingredient_id, batch_id, None, user["userid"], "Stock-In", qty)
    return {"ok": True, "batchId": batch_id}


def take_from_batches(cur, ingredient_id: int, qty, user_id: int | None,
                      movement_type: str, order_id: int | None = None, note: str | None = None) -> None:
    row = lock_ingredient(cur, ingredient_id)
    if row is None:
        raise ApiError(404, "Ingredient not found.")
    batches = list_fifo_batches(cur, ingredient_id)
    if sum((batch["qtyremaining"] for batch in batches), ZERO) < qty:
        raise ApiError(409, f"Not enough {row['name']} in stock.")
    left = qty
    for batch in batches:
        if left <= ZERO:
            break
        take = min(batch["qtyremaining"], left)
        consume_batch(cur, batch["batchid"], take)
        add_stock_movement(cur, ingredient_id, batch["batchid"], order_id, user_id, movement_type, take, note)
        left -= take


def consume_stock(cur, needs: dict, user_id: int, order_id: int) -> None:
    for ingredient_id, qty in needs.items():
        take_from_batches(cur, ingredient_id, qty, user_id, "Stock-Out", order_id)


def recipe_needs(cur, product_qtys) -> dict:
    needs = {}
    for product_id, qty in product_qtys:
        for row in recipe_rows(cur, product_id):
            ingredient_id = row["ingredientid"]
            needs[ingredient_id] = needs.get(ingredient_id, ZERO) + row["qtyused"] * qty
    return needs


def restore_stock(cur, order_id: int, user_id: int) -> None:
    for row in stock_movement_net(cur, order_id):
        net = row["net"]
        if net and net > 0:
            batch_id = create_stock_batch(cur, row["ingredientid"], f"RST-{order_id}", net)
            add_stock_movement(
                cur, row["ingredientid"], batch_id, order_id, user_id,
                "Restore", net, "Order cancelled",
            )


def stock_out_service(cur, user: dict, body: dict | None) -> dict:
    if not isinstance(body, dict):
        raise ApiError(422, "Send a JSON body.")
    ingredient_id = find_ingredient_service(cur, body)
    qty = positive_qty(body.get("quantity"))
    kind = body.get("type") or "Stock-Out"
    if kind not in ("Stock-Out", "Waste"):
        raise ApiError(422, "Type must be Stock-Out or Waste.")
    note = str(body.get("reason") or "").strip() or None
    if kind == "Waste" and not note:
        raise ApiError(422, "Enter a reason for the waste.")
    take_from_batches(cur, ingredient_id, qty, user["userid"], kind, None, note)
    return {"ok": True}
