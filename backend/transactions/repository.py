import psycopg2.errors
from transactions.models import SALE_STATUSES


SALE_SELECT = """
    SELECT o.orderid, o.ordernumber, o.customername, o.orderdatetime, o.discountamount, o.discountnote,
           o.servicecharge, o.totalamount, o.paymentmethod, o.orderstatus,
           o.voidreason, o.voidedat, vu.fullname AS voidedby,
           COALESCE((
               SELECT json_agg(json_build_object(
                          'name', oi.itemname, 'qty', oi.quantity,
                          'price', oi.unitprice, 'customization', oi.customization)
                      ORDER BY oi.orderitemid)
               FROM orderitem oi WHERE oi.orderid = o.orderid
           ), '[]'::json) AS items
    FROM orders o
    LEFT JOIN "User" vu ON vu.userid = o.voidedby
"""


REFUND_SELECT = """
    SELECT r.refundid, r.orderid, r.itemname, r.refundamount, r.reason, r.itemreturned,
           r.status, r.requestedat, r.approvedat,
           ru.fullname AS requestedby, au.fullname AS approvedby
    FROM refund r
    LEFT JOIN "User" ru ON ru.userid = r.requestedby
    LEFT JOIN "User" au ON au.userid = r.approvedby
"""


def fetch_sales(cur, tab: str, payment: str | None, query: str | None,
                date_from: str | None, date_to: str | None, limit: int) -> list[dict]:
    import re

    where, params = [], []
    if tab == "voided":
        where.append("o.orderstatus = 'Voided'")
    elif tab == "refunded":
        where.append("o.orderstatus = 'Refunded'")
    elif tab == "discounts":
        where.append("o.discountamount > 0")
        where.append("o.orderstatus = ANY(%s)")
        params.append(list(SALE_STATUSES))
    elif tab == "sales":
        where.append("o.orderstatus = ANY(%s)")
        params.append(list(SALE_STATUSES))
    else:
        return []
    if payment:
        where.append("o.paymentmethod = %s")
        params.append(payment)
    if query:
        clause = "o.ordernumber ILIKE %s"
        params.append(f"%{query}%")
        match = re.fullmatch(r"[sS]?(\d{1,9})", query)
        if match:
            clause += " OR o.orderid = %s"
            params.append(int(match.group(1)))
        where.append(f"({clause})")
    if date_from:
        where.append("o.orderdatetime::date >= %s")
        params.append(date_from)
    if date_to:
        where.append("o.orderdatetime::date <= %s")
        params.append(date_to)
    cur.execute(
        SALE_SELECT + " WHERE " + " AND ".join(where)
        + " ORDER BY o.orderdatetime DESC, o.orderid DESC LIMIT %s",
        params + [limit],
    )
    return cur.fetchall()


def fetch_refunds(cur, order_ids: list[int]) -> dict:
    if not order_ids:
        return {}
    cur.execute(
        REFUND_SELECT + " WHERE r.orderid = ANY(%s) ORDER BY r.refundid",
        (list(order_ids),),
    )
    grouped = {}
    for refund in cur.fetchall():
        grouped.setdefault(refund["orderid"], []).append(refund)
    return grouped


def get_sale_row(cur, order_id: int) -> dict | None:
    cur.execute(SALE_SELECT + " WHERE o.orderid = %s", (order_id,))
    return cur.fetchone()


def list_refunds(cur, status: str | None) -> list[dict]:
    sql, params = REFUND_SELECT, []
    if status:
        sql += " WHERE r.status = %s"
        params.append(status)
    cur.execute(sql + " ORDER BY r.refundid DESC", params)
    return cur.fetchall()


def lock_order(cur, order_id: int) -> dict | None:
    cur.execute(
        "SELECT orderid, orderstatus, totalamount FROM orders WHERE orderid = %s FOR UPDATE",
        (order_id,),
    )
    return cur.fetchone()


def create_refund(cur, order_id: int, amount, reason: str, item: str,
                  item_returned: bool, user_id: int) -> int:
    cur.execute(
        """INSERT INTO refund (orderid, refundamount, reason, itemreturned, status, requestedby, itemname)
           VALUES (%s, %s, %s, %s, 'Pending', %s, %s) RETURNING refundid""",
        (order_id, amount, reason, item_returned, user_id, item),
    )
    return cur.fetchone()["refundid"]


def find_pending_refund(cur, refund_id: int) -> dict | None:
    cur.execute("SELECT orderid FROM refund WHERE refundid = %s", (refund_id,))
    return cur.fetchone()


def lock_refund(cur, refund_id: int) -> dict | None:
    cur.execute("SELECT * FROM refund WHERE refundid = %s FOR UPDATE", (refund_id,))
    return cur.fetchone()


def update_refund(cur, refund_id: int, user_id: int, item: str, amount,
                  reason: str, returned: bool) -> None:
    cur.execute(
        """UPDATE refund SET status = 'Approved', approvedby = %s, approvedat = CURRENT_TIMESTAMP,
                  itemname = %s, refundamount = %s, reason = %s, itemreturned = %s
           WHERE refundid = %s""",
        (user_id, item, amount, reason, returned, refund_id),
    )


def reject_refund(cur, refund_id: int) -> None:
    cur.execute("UPDATE refund SET status = 'Rejected' WHERE refundid = %s", (refund_id,))


def reject_pending_refunds(cur, order_id: int) -> None:
    cur.execute("UPDATE refund SET status = 'Rejected' WHERE orderid = %s AND status = 'Pending'", (order_id,))


def set_order_refunded(cur, order_id: int) -> None:
    cur.execute("UPDATE orders SET orderstatus = 'Refunded' WHERE orderid = %s", (order_id,))


def refund_total_for_order(cur, order_id: int):
    cur.execute(
        "SELECT COALESCE(SUM(refundamount), 0) AS done FROM refund "
        "WHERE orderid = %s AND status = 'Approved'",
        (order_id,),
    )
    return cur.fetchone()["done"]


def refund_item_exists(cur, order_id: int, item: str) -> bool:
    cur.execute("SELECT 1 FROM orderitem WHERE orderid = %s AND itemname = %s", (order_id, item))
    return cur.fetchone() is not None


def void_order(cur, order_id: int, reason: str, user_id: int) -> None:
    cur.execute(
        """UPDATE orders SET orderstatus = 'Voided', voidreason = %s, voidedby = %s,
           voidedat = CURRENT_TIMESTAMP WHERE orderid = %s""",
        (reason, user_id, order_id),
    )
