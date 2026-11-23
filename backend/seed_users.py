"""Create/reset the local development Owner and Barista accounts.

Run after schema.sql. Passwords can be overridden with BB_OWNER_PASSWORD and
BB_BARISTA_PASSWORD in backend/.env; defaults are for local development only.
"""
import os

from werkzeug.security import generate_password_hash

from db import get_conn


USERS = (
    ("Owner", "owner", "BB_OWNER_PASSWORD", "owner123"),
    ("Barista", "barista", "BB_BARISTA_PASSWORD", "barista123"),
)


def main():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            for fullname, username, env_name, default_password in USERS:
                password = os.getenv(env_name, default_password)
                cur.execute(
                    'INSERT INTO "User" (FullName, Username, Password, Role, IsActive) '
                    'VALUES (%s, %s, %s, %s, TRUE) '
                    'ON CONFLICT (Username) DO UPDATE SET '
                    'FullName = EXCLUDED.FullName, Password = EXCLUDED.Password, '
                    'Role = EXCLUDED.Role, IsActive = TRUE',
                    (fullname, username, generate_password_hash(password), username.title()),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    print("Local Owner and Barista accounts are ready.")
    print("Set BB_OWNER_PASSWORD and BB_BARISTA_PASSWORD in backend/.env before real use.")


if __name__ == "__main__":
    main()
