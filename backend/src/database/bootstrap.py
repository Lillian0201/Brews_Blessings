import os

import psycopg2
from psycopg2 import sql

from src.config import BACKEND_ROOT, get_bool, get_env
from src.database.connection import get_conn


def ensure_database() -> None:
    # Supabase creates the project's database for you and does not grant the
    # app role permission to create databases. Schema bootstrap still runs in
    # apply_bootstrap() after this check.
    if os.getenv("DATABASE_URL", "").strip():
        return

    db_name = get_env("DB_NAME")
    admin_name = get_env("DB_ADMIN_NAME", "postgres")
    conn = psycopg2.connect(
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        dbname=admin_name,
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cur.fetchone() is None:
                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
                )
                print("Database created.")
    except psycopg2.errors.InsufficientPrivilege:
        raise RuntimeError("Database privileges are insufficient to create the configured database.")
    finally:
        conn.close()


def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND lower(table_name) = lower(%s))",
        (table_name,),
    )
    return bool(cur.fetchone()[0])


def apply_bootstrap() -> None:
    ensure_database()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(hashtext(%s))", ("brews_blessings_bootstrap",))
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(filename VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        conn.commit()

        for filename, baseline_check in (
            ("schema.sql", lambda cur: table_exists(cur, "product")),
            ("migrations/001_transactions.sql", lambda cur: table_exists(cur, "orderitem")),
            ("migrations/002_inventory_pos.sql", lambda cur: table_exists(cur, "ingredient")),
        ):
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,))
                if cur.fetchone():
                    continue
                if filename != "schema.sql" and baseline_check(cur):
                    cur.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (filename,),
                    )
                    conn.commit()
                    print(f"Migration baseline recorded: {filename}")
                    continue

                path = BACKEND_ROOT / filename
                cur.execute(path.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)",
                    (filename,),
                )
            conn.commit()
            print(f"Applied: {filename}")

        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", ("brews_blessings_bootstrap",))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
