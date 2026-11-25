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


def list_inventory(cur) -> list[dict]:
    cur.execute(INGREDIENT_SQL)
    return cur.fetchall()


def list_movements(cur) -> list[dict]:
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
    return cur.fetchall()


def find_ingredient(cur, ingredient_id: int | None = None, barcode: str | None = None) -> dict | None:
    if ingredient_id is not None:
        cur.execute("SELECT ingredientid FROM ingredient WHERE ingredientid = %s", (ingredient_id,))
    elif barcode:
        cur.execute("SELECT ingredientid FROM ingredient WHERE barcode = %s", (barcode,))
    else:
        return None
    return cur.fetchone()


def ingredient_name_exists(cur, name: str) -> bool:
    cur.execute("SELECT 1 FROM ingredient WHERE lower(name) = lower(%s)", (name,))
    return cur.fetchone() is not None


def add_ingredient(cur, name: str, barcode: str | None, unit: str, unit_cost, reorder) -> int:
    cur.execute(
        "INSERT INTO ingredient (name, barcode, unit, unitcost, reorderlevel) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING ingredientid",
        (name[:60], barcode, unit[:20], unit_cost, reorder),
    )
    return cur.fetchone()["ingredientid"]


def create_stock_batch(cur, ingredient_id: int, batch_no: str, qty) -> int:
    cur.execute(
        "INSERT INTO stockbatch (ingredientid, batchno, qtyreceived, qtyremaining) "
        "VALUES (%s, %s, %s, %s) RETURNING batchid",
        (ingredient_id, batch_no, qty, qty),
    )
    return cur.fetchone()["batchid"]


def add_stock_movement(cur, ingredient_id: int, batch_id: int | None, order_id: int | None,
                       user_id: int | None, movement_type: str, quantity, note: str | None = None) -> None:
    cur.execute(
        "INSERT INTO stockmovement (ingredientid, batchid, orderid, userid, movementtype, quantity, note) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (ingredient_id, batch_id, order_id, user_id, movement_type, quantity, note),
    )


def lock_ingredient(cur, ingredient_id: int) -> dict | None:
    cur.execute("SELECT name FROM ingredient WHERE ingredientid = %s FOR UPDATE", (ingredient_id,))
    return cur.fetchone()


def list_fifo_batches(cur, ingredient_id: int) -> list[dict]:
    cur.execute(
        "SELECT batchid, qtyremaining FROM stockbatch "
        "WHERE ingredientid = %s AND qtyremaining > 0 "
        "ORDER BY receiveddate, batchid FOR UPDATE",
        (ingredient_id,),
    )
    return cur.fetchall()


def consume_batch(cur, batch_id: int, take) -> None:
    cur.execute("UPDATE stockbatch SET qtyremaining = qtyremaining - %s WHERE batchid = %s", (take, batch_id))


def recipe_rows(cur, product_id: int) -> list[dict]:
    cur.execute("SELECT ingredientid, qtyused FROM recipe WHERE productid = %s", (product_id,))
    return cur.fetchall()


def stock_movement_net(cur, order_id: int) -> list[dict]:
    cur.execute(
        "SELECT ingredientid, SUM(CASE WHEN movementtype = 'Stock-Out' THEN quantity "
        "                              WHEN movementtype = 'Restore' THEN -quantity "
        "                              ELSE 0 END) AS net "
        "FROM stockmovement WHERE orderid = %s GROUP BY ingredientid",
        (order_id,),
    )
    return cur.fetchall()
