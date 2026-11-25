def find_login_user(cur, username: str) -> dict | None:
    cur.execute(
        'SELECT userid, fullname, username, role, password, isactive FROM "User" '
        "WHERE lower(username) = lower(%s)",
        (username,),
    )
    return cur.fetchone()
