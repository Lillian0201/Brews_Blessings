PRODUCT_SELECT = """
    SELECT productid, productname, category::text AS category, sellingprice,
           grandeurprice, hotprice, productcost, packagingcost, isavailable
    FROM product
"""


def list_products(cur, available: bool | None = None) -> list[dict]:
    sql = PRODUCT_SELECT
    params = []
    if available is True:
        sql += " WHERE isavailable"
    cur.execute(sql + " ORDER BY category, productname", params)
    return cur.fetchall()


def get_product(cur, product_id: int) -> dict | None:
    cur.execute(PRODUCT_SELECT + " WHERE productid = %s", (product_id,))
    return cur.fetchone()


def name_exists(cur, name: str, ignore_id: int | None = None) -> bool:
    cur.execute(
        "SELECT 1 FROM product WHERE lower(productname) = lower(%s) AND productid <> COALESCE(%s, -1)",
        (name, ignore_id),
    )
    return cur.fetchone() is not None


def add_product(cur, name: str, category: str, price, grandeur_price, hot_price, packaging: float, available: bool) -> int:
    cur.execute(
        """INSERT INTO product
           (productname, category, sellingprice, grandeurprice, hotprice, packagingcost, isavailable)
           VALUES (%s, %s::product_category, %s, %s, %s, %s, %s) RETURNING productid""",
        (name, category, price, grandeur_price, hot_price, packaging, available),
    )
    return cur.fetchone()["productid"]


def update_product(cur, product_id: int, name: str, category: str, price, grandeur_price, hot_price, packaging, available: bool) -> None:
    cur.execute(
        """UPDATE product SET productname = %s, category = %s::product_category, sellingprice = %s,
                  grandeurprice = %s, hotprice = %s, packagingcost = %s, isavailable = %s
           WHERE productid = %s""",
        (name, category, price, grandeur_price, hot_price, packaging, available, product_id),
    )


def product_is_used(cur, product_id: int) -> bool:
    cur.execute(
        """SELECT EXISTS (SELECT 1 FROM orderitem WHERE productid = %s)
               OR EXISTS (SELECT 1 FROM inventory WHERE productid = %s) AS used""",
        (product_id, product_id),
    )
    return bool(cur.fetchone()["used"])


def hide_product(cur, product_id: int) -> None:
    cur.execute("UPDATE product SET isavailable = FALSE WHERE productid = %s", (product_id,))


def delete_product(cur, product_id: int) -> None:
    cur.execute("DELETE FROM product WHERE productid = %s", (product_id,))
