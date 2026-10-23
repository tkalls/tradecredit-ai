"""One worked example of the pattern. Write the rest of the tests in test_notes.py."""

from fastapi.testclient import TestClient


def test_create_returns_201_and_the_full_note(client: TestClient) -> None:
    response = client.post("/notes", json={"title": "Buy milk", "body": "2 litres"})

    assert response.status_code == 201
    note = response.json()
    assert note["title"] == "Buy milk"
    assert note["body"] == "2 litres"
    assert isinstance(note["id"], int)  # the server chose it
    assert "created_at" in note  # the server chose it
