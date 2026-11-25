from pos.models import ORDER_COLUMNS


def find_available_product(cur, product_id: int) -> dict | None:
    cur.execute(
        "SELECT productname, sellingprice, grandeurprice, hotprice FROM product "
        "WHERE productid = %s AND isavailable",
        (product_id,),
    )
    return cur.fetchone()


def next_order_number(cur) -> str:
    cur.execute("SELECT COALESCE(MAX(CASE WHEN ordernumber ~ '^[0-9]+$'"
                " THEN CAST(ordernumber AS INT) END), 0) + 1 AS n FROM orders")
    return f"{cur.fetchone()['n']:03d}"


def create_order(cur, user_id: int, order_number: str, customer: str, total,
                 discount, payment: str, tendered, discount_note: str = "") -> int:
    cur.execute(
        "INSERT INTO orders (userid, ordernumber, customername, totalamount, discountamount, "
        "discountnote, paymentmethod, amounttendered, orderstatus) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pending') RETURNING orderid",
        (user_id, order_number, customer, total, discount, discount_note, payment, tendered),
    )
    return cur.fetchone()["orderid"]


def add_order_item(cur, order_id: int, product_id: int, name: str, qty: int, price, customization) -> None:
    cur.execute(
        "INSERT INTO orderitem (orderid, productid, itemname, quantity, unitprice, customization) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (order_id, product_id, name, qty, price, customization),
    )


def list_orders(cur) -> list[dict]:
    cur.execute(
        f"SELECT {ORDER_COLUMNS} FROM orders "
        "WHERE orderdatetime::date = CURRENT_DATE ORDER BY orderdatetime DESC"
    )
    return cur.fetchall()


def get_order(cur, order_id: int) -> dict | None:
    cur.execute(f"SELECT {ORDER_COLUMNS} FROM orders WHERE orderid = %s", (order_id,))
    return cur.fetchone()


def list_order_items(cur, order_id: int) -> list[dict]:
    cur.execute(
        "SELECT itemname, quantity, unitprice, customization FROM orderitem "
        "WHERE orderid = %s ORDER BY orderitemid",
        (order_id,),
    )
    return cur.fetchall()


def lock_order_status(cur, order_id: int) -> dict | None:
    cur.execute("SELECT orderstatus FROM orders WHERE orderid = %s FOR UPDATE", (order_id,))
    return cur.fetchone()


def set_order_status(cur, order_id: int, status: str, cancel_reason: str | None = None) -> None:
    cur.execute(
        "UPDATE orders SET orderstatus = %s, cancelreason = %s WHERE orderid = %s",
        (status, cancel_reason, order_id),
    )


def order_recipe_rows(cur, order_id: int) -> list[dict]:
    cur.execute(
        "SELECT productid, quantity FROM orderitem "
        "WHERE orderid = %s AND productid IS NOT NULL",
        (order_id,),
    )
    return cur.fetchall()
