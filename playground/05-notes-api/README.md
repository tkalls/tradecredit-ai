# 05: Notes API

Basics exercises 5 (HTTP and REST) and 8 (testing): a FastAPI CRUD API for notes, on Postgres, with tests.

## What it does

| Method and path | Does | Success | Errors |
| --- | --- | --- | --- |
| `POST /notes` | create a note | 201 + the note | 422 bad body |
| `GET /notes` | list all notes, oldest first | 200 | |
| `GET /notes/{id}` | get one note | 200 | 404, 422 non-number id |
| `PATCH /notes/{id}` | change only the fields sent | 200 | 404, 422 |
| `DELETE /notes/{id}` | delete a note | 204 | 404 |

Three Pydantic models, one per crossing: `NoteCreate` (client sends title + body), `NoteUpdate` (client sends
either, both optional), `Note` (server sends all four fields; `id` and `created_at` are decided by Postgres).

## Where the database lives

Postgres 16 runs in Docker Compose on my home server (Cerebro), bound to its localhost only. The Mac reaches it
through an SSH tunnel, so the database is never exposed on the network. Synthetic data only.

## Run it

```bash
ssh -N cerebro-db                  # second terminal tab: opens the tunnel to 127.0.0.1:5432
cp .env.example .env               # then put in the database password
uv run --env-file .env python -c "import os, psycopg; c = psycopg.connect(os.environ['DATABASE_URL']); c.execute(open('schema.sql').read()); c.commit()"
uv run --env-file .env uvicorn notes_api.main:app --reload
```

Then open http://127.0.0.1:8000/docs.

## Check it

```bash
uv run ruff check . && uv run mypy notes_api && uv run --env-file .env pytest
```

Each test runs in its own throwaway schema inside a transaction that is rolled back, so tests never touch real
notes. These tests need the database, so they run locally, not in CI (CI covers `backend/` only).
