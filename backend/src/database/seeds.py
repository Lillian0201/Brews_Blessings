from src.config import BACKEND_ROOT, get_bool, get_env
from src.core.security import hash_password
from src.database.connection import get_conn


def seed_products(cur) -> None:
    cur.execute((BACKEND_ROOT / "seed_products.sql").read_text(encoding="utf-8"))


def seed_users(cur) -> None:
    users = [
        ("Owner", "owner", get_env("BB_OWNER_PASSWORD", "owner123")),
        ("Barista", "barista", get_env("BB_BARISTA_PASSWORD", "barista123")),
    ]
    # Set BB_ADMIN_PASSWORD to provision the first Admin account. Once one
    # exists, Admin accounts can be managed from System Maintenance.
    admin_password = get_env("BB_ADMIN_PASSWORD", "")
    if admin_password:
        users.append(("Admin", "admin", admin_password))
    for fullname, username, password in users:
        cur.execute(
            'INSERT INTO "User" (fullname, username, password, role, isactive) '
            "VALUES (%s, %s, %s, %s, TRUE) "
            "ON CONFLICT (username) DO NOTHING",
            (fullname, username, hash_password(password), fullname),
        )


def seed_transactions(cur) -> None:
    cur.execute((BACKEND_ROOT / "seed_transactions.sql").read_text(encoding="utf-8"))


def run_seeds() -> None:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            seed_products(cur)
            seed_users(cur)
            if get_bool("BB_SEED_SAMPLE_DATA", True):
                seed_transactions(cur)
        conn.commit()
        print("Seeding complete.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
