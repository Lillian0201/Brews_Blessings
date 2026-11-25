from psycopg2.extensions import connection


def audit(cur, user_id: int | None, action: str, table_name: str, record_id: int | None) -> None:
    cur.execute(
        "INSERT INTO auditlog (userid, action, tablename, recordid) VALUES (%s, %s, %s, %s)",
        (user_id, action, table_name, record_id),
    )
