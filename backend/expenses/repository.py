EXPENSE_SELECT = """
    SELECT e.expenseid, e.expensedate, e.expensetype, e.description, e.amount,
           u.fullname AS recordedby
    FROM expense e
    LEFT JOIN "User" u ON u.userid = e.userid
"""


def list_expenses(cur, etype: str | None, date_from: str | None, date_to: str | None, limit: int) -> list[dict]:
    where, params = [], []
    if etype:
        where.append("e.expensetype = %s")
        params.append(etype)
    if date_from:
        where.append("e.expensedate >= %s")
        params.append(date_from)
    if date_to:
        where.append("e.expensedate <= %s")
        params.append(date_to)
    sql = EXPENSE_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    cur.execute(sql + " ORDER BY e.expensedate DESC, e.expenseid DESC LIMIT %s", params + [limit])
    return cur.fetchall()


def add_expense(cur, user_id: int, etype: str, description: str, amount, spent_on) -> int:
    cur.execute(
        """INSERT INTO expense (userid, expensetype, description, amount, expensedate)
           VALUES (%s, %s, %s, %s, %s) RETURNING expenseid""",
        (user_id, etype, description, amount, spent_on),
    )
    return cur.fetchone()["expenseid"]


def get_expense(cur, expense_id: int) -> dict | None:
    cur.execute(EXPENSE_SELECT + " WHERE e.expenseid = %s", (expense_id,))
    return cur.fetchone()
