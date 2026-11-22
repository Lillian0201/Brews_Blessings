"""
Dashboard API: today's numbers for the Dashboard page.
"Today" is the database server's date (CURRENT_DATE).
"""
from flask import Blueprint, jsonify
from transactions import ApiError, current_user, handle_api_error, num, with_db

bp = Blueprint("dashboard", __name__, url_prefix="/api")
bp.register_error_handler(ApiError, handle_api_error)


@bp.get("/dashboard/summary")
@with_db
def summary(cur):
    current_user(cur)

    cur.execute("""
        SELECT
            COALESCE(SUM(totalamount) FILTER (WHERE orderstatus IN ('Completed', 'Refunded')), 0) AS gross,
            COUNT(*) AS orders_today,
            COUNT(*) FILTER (WHERE orderstatus = 'Pending')   AS pending,
            COUNT(*) FILTER (WHERE orderstatus = 'Completed') AS completed,
            COUNT(*) FILTER (WHERE orderstatus = 'Cancelled') AS cancelled
        FROM orders
        WHERE orderdatetime::date = CURRENT_DATE
    """)
    o = cur.fetchone()

    cur.execute("SELECT COALESCE(SUM(refundamount), 0) AS total FROM refund "
                "WHERE status = 'Approved' AND approvedat::date = CURRENT_DATE")
    refund_total = cur.fetchone()["total"]

    cur.execute("SELECT COALESCE(SUM(amount), 0) AS total FROM expense "
                "WHERE expensedate = CURRENT_DATE")
    expense_total = cur.fetchone()["total"]

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
    best = [{"name": r["itemname"], "qty": num(r["qty"]), "sales": num(r["sales"])}
            for r in cur.fetchall()]

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
    stock = cur.fetchone()

    gross = num(o["gross"])
    refunds = num(refund_total)
    return jsonify({
        "todaySales": gross,
        "refunds": refunds,
        "netSales": gross - refunds,
        "ordersToday": o["orders_today"],
        "pending": o["pending"],
        "completed": o["completed"],
        "cancelled": o["cancelled"],
        "expensesToday": num(expense_total),
        "bestSellers": best,
        "availableStock": stock["available"],
        "lowStock": stock["low"],
        "outOfStock": stock["out"],
        "stockAlerts": stock["low"] + stock["out"],
    })