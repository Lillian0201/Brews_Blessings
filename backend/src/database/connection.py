import os
from collections.abc import Generator

import psycopg2
from fastapi import Request
from psycopg2.extras import RealDictCursor

from src.config import get_env


def get_conn():
    # Supabase provides a PostgreSQL URL. Keep the individual settings for
    # local development, but prefer the URL when one is configured.
    database_url = get_env("DATABASE_URL") if os.getenv("DATABASE_URL", "").strip() else None
    if database_url:
        return psycopg2.connect(database_url, sslmode="require")

    return psycopg2.connect(
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
        sslmode=get_env("DB_SSLMODE", "prefer"),
    )


def get_cursor(request: Request) -> Generator[RealDictCursor, None, None]:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        request.state.db_connection = conn
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur = locals().get("cur")
        if cur is not None:
            cur.close()
        conn.close()
