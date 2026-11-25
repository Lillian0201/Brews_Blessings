USER_SELECT = 'SELECT userid, fullname, username, role, isactive FROM "User"'


def list_users(cur) -> list[dict]:
    cur.execute(USER_SELECT + " ORDER BY userid")
    return cur.fetchall()


def get_user(cur, user_id: int) -> dict | None:
    cur.execute(USER_SELECT + " WHERE userid = %s", (user_id,))
    return cur.fetchone()


def username_exists(cur, username: str) -> bool:
    cur.execute('SELECT 1 FROM "User" WHERE lower(username) = lower(%s)', (username,))
    return cur.fetchone() is not None


def add_user(cur, name: str, username: str, password_hash: str, role: str) -> int:
    cur.execute(
        'INSERT INTO "User" (fullname, username, password, role) VALUES (%s, %s, %s, %s) RETURNING userid',
        (name, username, password_hash, role),
    )
    return cur.fetchone()["userid"]


def active_owner_count(cur, exclude_user_id: int) -> int:
    cur.execute(
        """SELECT COUNT(*) AS n FROM "User"
           WHERE role = 'Owner' AND isactive AND userid <> %s""",
        (exclude_user_id,),
    )
    return cur.fetchone()["n"]


def update_user(cur, user_id: int, name: str, role: str, active: bool) -> None:
    cur.execute(
        'UPDATE "User" SET fullname = %s, role = %s, isactive = %s WHERE userid = %s',
        (name, role, active, user_id),
    )
