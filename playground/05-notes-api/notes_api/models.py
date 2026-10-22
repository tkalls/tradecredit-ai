from datetime import datetime

from pydantic import BaseModel


class NoteCreate(BaseModel):
    """What a client may send to create a note (POST /notes)."""

    title: str
    body: str


class NoteUpdate(BaseModel):
    """What a client may send to change a note (PATCH /notes/{id}). Send only what changes."""

    title: str | None = None
    body: str | None = None


class Note(NoteCreate):
    """What the server sends back: the client's fields plus the two the server decides."""

    id: int
    created_at: datetime
