def dashboard_totals(cur) -> dict:
    cur.execute("""
        SELECT
            COALESCE(SUM(totalamount) FILTER (WHERE orderstatus IN ('Completed', 'Refunded')), 0) AS gross,
            COUNT(*) AS orders_today,
            COUNT(*) FILTER (WHERE orderstatus = 'Pending') AS pending,
            COUNT(*) FILTER (WHERE orderstatus = 'Completed') AS completed,
            COUNT(*) FILTER (WHERE orderstatus = 'Cancelled') AS cancelled
        FROM orders
        WHERE orderdatetime::date = CURRENT_DATE
    """)
    return cur.fetchone()


def today_refunds(cur):
    cur.execute(
        "SELECT COALESCE(SUM(refundamount), 0) AS total FROM refund "
        "WHERE status = 'Approved' AND approvedat::date = CURRENT_DATE"
    )
    return cur.fetchone()["total"]


def today_expenses(cur):
    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total FROM expense "
        "WHERE expensedate = CURRENT_DATE"
    )
    return cur.fetchone()["total"]


def best_sellers(cur) -> list[dict]:
    cur.execute("""
        SELECT oi.itemname, SUM(oi.quantity) AS qty, SUM(oi.quantity * oi.unitprice) AS sales
        FROM orderitem oi
        JOIN orders o ON o.orderid = oi.orderid
        WHERE o.orderdatetime::date = CURRENT_DATE
          AND o.orderstatus IN ('Completed', 'Refunded')
        GROUP BY oi.itemname
        ORDER BY qty DESC, oi.itemname
        LIMIT 5
    """)
    return cur.fetchall()


def stock_counts(cur) -> dict:
    cur.execute("""
        WITH s AS (
            SELECT i.reorderlevel, COALESCE(SUM(b.qtyremaining), 0) AS remaining
            FROM ingredient i
            LEFT JOIN stockbatch b ON b.ingredientid = i.ingredientid
            WHERE i.isactive
            GROUP BY i.ingredientid, i.reorderlevel
        )
        SELECT
            COUNT(*) FILTER (WHERE remaining > reorderlevel) AS available,
            COUNT(*) FILTER (WHERE remaining > 0 AND remaining <= reorderlevel) AS low,
            COUNT(*) FILTER (WHERE remaining <= 0) AS out
        FROM s
    """)
    return cur.fetchone()
