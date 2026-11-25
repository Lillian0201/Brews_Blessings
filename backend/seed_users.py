"""Create/reset the Owner and Barista accounts.

Run after the schema migrations with BB_OWNER_PASSWORD and BB_BARISTA_PASSWORD set.
"""
from src.config import get_env
from src.core.security import hash_password
from src.database.connection import get_conn


USERS = (
    ("Owner", "owner", "BB_OWNER_PASSWORD"),
    ("Barista", "barista", "BB_BARISTA_PASSWORD"),
)


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for fullname, username, env_name in USERS:
                password = get_env(env_name)
                cur.execute(
                    'INSERT INTO "User" (FullName, Username, Password, Role, IsActive) '
                    'VALUES (%s, %s, %s, %s, TRUE) '
                    'ON CONFLICT (Username) DO UPDATE SET '
                    'FullName = EXCLUDED.FullName, Password = EXCLUDED.Password, '
                    'Role = EXCLUDED.Role, IsActive = TRUE RETURNING UserID',
                    (fullname, username, hash_password(password), username.title()),
                )
                user_id = cur.fetchone()[0]
                cur.execute(
                    "DELETE FROM app_sessions WHERE user_id = %s",
                    (user_id,),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Owner and Barista accounts are ready.")


if __name__ == "__main__":
    main()
