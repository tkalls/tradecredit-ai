"""Test fixtures: every test runs inside one transaction that is rolled back at the end.

The test makes its own empty schema, runs schema.sql in it, and points the app at it.
Postgres can undo all of that, table creation included, so a test leaves nothing behind
and never sees your real notes.
"""

from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row

from notes_api.db import Conn, database_url, get_conn

SCHEMA = Path(__file__).parent.parent / "schema.sql"


@pytest.fixture
def conn() -> Iterator[Conn]:
    with psycopg.connect(database_url(), row_factory=dict_row) as c:
        c.execute("CREATE SCHEMA notes_test")
        c.execute("SET LOCAL search_path TO notes_test")
        c.execute(SCHEMA.read_text())
        yield c
        c.rollback()


@pytest.fixture
def client(conn: Conn) -> Iterator[TestClient]:
    from notes_api.main import app

    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()
