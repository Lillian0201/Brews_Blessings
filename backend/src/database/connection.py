import os
from collections.abc import Generator

import psycopg2
from fastapi import Request
from psycopg2.extras import RealDictCursor

from src.config import get_env


def get_conn():
    return psycopg2.connect(
        host=get_env("DB_HOST"),
        port=get_env("DB_PORT"),
        dbname=get_env("DB_NAME"),
        user=get_env("DB_USER"),
        password=get_env("DB_PASSWORD"),
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
