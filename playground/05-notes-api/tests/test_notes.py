"""Tests for the notes API. Each test gets an empty notes table (see conftest.py)."""

from fastapi.testclient import TestClient


def make_note(client: TestClient, title: str = "Buy milk", body: str = "2 litres") -> int:
    """Create a note through the API and return its id."""
    response = client.post("/notes", json={"title": title, "body": body})
    assert response.status_code == 201
    return int(response.json()["id"])


def test_get_returns_the_note(client: TestClient) -> None:
    note_id = make_note(client)

    response = client.get(f"/notes/{note_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "Buy milk"


def test_get_missing_note_is_404(client: TestClient) -> None:
    response = client.get("/notes/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Note not found"}


def test_get_non_number_id_is_422(client: TestClient) -> None:
    response = client.get("/notes/abc")

    assert response.status_code == 422


def test_list_returns_all_notes_in_order(client: TestClient) -> None:
    first = make_note(client, title="First")
    second = make_note(client, title="Second")

    response = client.get("/notes")

    assert response.status_code == 200
    assert [n["id"] for n in response.json()] == [first, second]


def test_list_is_empty_at_start(client: TestClient) -> None:
    assert client.get("/notes").json() == []


def test_patch_changes_only_what_was_sent(client: TestClient) -> None:
    note_id = make_note(client, title="Buy milk", body="2 litres")

    response = client.patch(f"/notes/{note_id}", json={"title": "Buy oat milk"})

    assert response.status_code == 200
    assert response.json()["title"] == "Buy oat milk"
    assert response.json()["body"] == "2 litres"  # kept: it wasn't sent


def test_patch_missing_note_is_404(client: TestClient) -> None:
    response = client.patch("/notes/999999", json={"title": "x"})

    assert response.status_code == 404


def test_create_without_body_is_422(client: TestClient) -> None:
    response = client.post("/notes", json={"title": "No body"})

    assert response.status_code == 422


def test_delete_removes_the_note(client: TestClient) -> None:
    note_id = make_note(client)

    response = client.delete(f"/notes/{note_id}")

    assert response.status_code == 204
    assert client.get(f"/notes/{note_id}").status_code == 404


def test_delete_missing_note_is_404(client: TestClient) -> None:
    assert client.delete("/notes/999999").status_code == 404
