"""Database connection for the notes API.

Each request gets its own connection. psycopg's `with` block commits when the
request finishes without an error and rolls back when it raises.
"""

import os
from collections.abc import Iterator

import psycopg
from psycopg.rows import DictRow, dict_row

Conn = psycopg.Connection[DictRow]


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set: copy .env.example to .env and fill it in")
    return url


def get_conn() -> Iterator[Conn]:
    """FastAPI dependency: routes ask for it with `conn: Conn = Depends(get_conn)`."""
    with psycopg.connect(database_url(), row_factory=dict_row) as conn:
        yield conn
