from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from notes_api.db import Conn, get_conn
from notes_api.models import Note, NoteCreate, NoteUpdate

app = FastAPI(title="Notes API")

# "A database connection, supplied by get_conn". Routes take `conn: DbConn`.
DbConn = Annotated[Conn, Depends(get_conn)]


def not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")


@app.post("/notes", response_model=Note, status_code=status.HTTP_201_CREATED)
def create_note(note: NoteCreate, conn: DbConn) -> Note:
    row = conn.execute(
        "INSERT INTO notes (title, body) VALUES (%s, %s) RETURNING *",
        (note.title, note.body),
    ).fetchone()
    if row is None:  # INSERT ... RETURNING always gives back the row
        raise RuntimeError("INSERT returned no row")
    return Note(**row)


@app.get("/notes", response_model=list[Note])
def list_notes(conn: DbConn) -> list[Note]:
    rows = conn.execute("SELECT * FROM notes ORDER BY id").fetchall()
    return [Note(**row) for row in rows]


@app.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: int, conn: DbConn) -> Note:
    row = conn.execute("SELECT * FROM notes WHERE id = %s", (note_id,)).fetchone()
    if row is None:
        raise not_found()
    return Note(**row)


@app.patch("/notes/{note_id}", response_model=Note)
def update_note(note_id: int, changes: NoteUpdate, conn: DbConn) -> Note:
    row = conn.execute(
        "UPDATE notes SET title = COALESCE(%s, title), body = COALESCE(%s, body)"
        " WHERE id = %s RETURNING *",
        (changes.title, changes.body, note_id),
    ).fetchone()
    if row is None:
        raise not_found()
    return Note(**row)


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int, conn: DbConn) -> None:
    deleted = conn.execute("DELETE FROM notes WHERE id = %s", (note_id,)).rowcount
    if deleted == 0:
        raise not_found()
