"""End-to-end API tests using FastAPI's TestClient.

These cover the review-checklist items: all CRUD operations, data persistence,
input validation, and missing-record handling.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID = {
    "name": "Test Student",
    "date_of_birth": "2004-05-01",
    "email": "test.student@example.com",
    "course": "Computer Science",
}


def _create(**overrides):
    payload = {**VALID, **overrides}
    return client.post("/students", json=payload)


def test_create_and_read():
    resp = _create()
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] >= 1
    assert body["name"] == "Test Student"

    # Read it back (persisted).
    got = client.get(f"/students/{body['id']}")
    assert got.status_code == 200
    assert got.json()["email"] == "test.student@example.com"


def test_create_requires_a_contact():
    resp = _create(email=None, phone=None)
    assert resp.status_code == 422  # validation error


def test_create_rejects_future_dob():
    resp = _create(date_of_birth="2999-01-01")
    assert resp.status_code == 422


def test_get_missing_returns_404():
    assert client.get("/students/999999").status_code == 404


def test_update_student():
    student_id = _create().json()["id"]
    resp = client.patch(f"/students/{student_id}", json={"course": "Data Science"})
    assert resp.status_code == 200
    assert resp.json()["course"] == "Data Science"


def test_update_missing_returns_404():
    assert client.patch("/students/999999", json={"course": "X"}).status_code == 404


def test_update_cannot_remove_last_contact():
    # Student created with email only; clearing it must be rejected.
    student_id = _create(phone=None).json()["id"]
    resp = client.patch(f"/students/{student_id}", json={"email": None})
    assert resp.status_code == 400


def test_delete_student():
    student_id = _create().json()["id"]
    assert client.delete(f"/students/{student_id}").status_code == 200
    assert client.get(f"/students/{student_id}").status_code == 404


def test_delete_missing_returns_404():
    assert client.delete("/students/999999").status_code == 404


def test_list_and_filter_born_after():
    _create(name="Older", date_of_birth="2000-01-01")
    _create(name="Younger", date_of_birth="2008-01-01")

    all_students = client.get("/students").json()
    assert len(all_students) == 2

    younger = client.get("/students", params={"born_after": "2005-01-01"}).json()
    assert [s["name"] for s in younger] == ["Younger"]


def test_search_by_name():
    _create(name="Alice Example")
    _create(name="Bob Example")
    hits = client.get("/students", params={"search": "alice"}).json()
    assert len(hits) == 1
    assert hits[0]["name"] == "Alice Example"
