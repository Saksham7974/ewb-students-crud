"""End-to-end API tests using FastAPI's TestClient.

These cover the review-checklist items: all CRUD operations, data persistence,
input validation, and missing-record handling.
"""
import itertools
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

_counter = itertools.count(1)

VALID = {
    "name": "Test Student",
    "date_of_birth": "2004-05-01",
    "email": "test.student@example.com",
    "course": "Computer Science",
}


def _create(**overrides):
    payload = dict(VALID)
    if "email" not in overrides and "phone" not in overrides:
        payload["email"] = f"student_{next(_counter)}@example.com"
    payload.update(overrides)
    return client.post("/students", json=payload)


def test_create_and_read():
    resp = _create(email="test.student@example.com")
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


def test_create_rejects_duplicate_email():
    resp1 = _create(email="dup.student@example.com")
    assert resp1.status_code == 201

    # Exact duplicate
    resp2 = _create(email="dup.student@example.com")
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"]

    # Case-insensitive duplicate
    resp3 = _create(email="DUP.STUDENT@EXAMPLE.COM")
    assert resp3.status_code == 409


def test_update_put_and_patch():
    student_id = _create(name="Initial Name", course="Math").json()["id"]

    # PUT request
    put_resp = client.put(
        f"/students/{student_id}",
        json={"name": "Put Name", "course": "Physics"},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == "Put Name"
    assert put_resp.json()["course"] == "Physics"

    # PATCH request
    patch_resp = client.patch(
        f"/students/{student_id}",
        json={"course": "Chemistry"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Put Name"
    assert patch_resp.json()["course"] == "Chemistry"


def test_update_rejects_duplicate_email():
    id1 = _create(email="student.one@example.com").json()["id"]
    id2 = _create(email="student.two@example.com").json()["id"]

    # Trying to update student 2 to use student 1's email must fail with 409
    resp = client.patch(f"/students/{id2}", json={"email": "student.one@example.com"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]

    # Updating student 2 with its own email should succeed (not flagged as duplicate of self)
    resp_self = client.patch(f"/students/{id2}", json={"email": "student.two@example.com", "course": "Biology"})
    assert resp_self.status_code == 200
    assert resp_self.json()["course"] == "Biology"


def test_create_rejects_blank_name():
    resp = _create(name="   ")
    assert resp.status_code == 422


def test_create_rejects_malformed_email():
    resp = _create(email="not-a-valid-email")
    assert resp.status_code == 422


def test_database_persistence():
    # Verify that a created student is truly written to the underlying SQLite database
    import sqlite3
    import os

    db_file = os.environ.get("STUDENTS_DB")
    created = _create(name="Persistent Student", email="persist@example.com").json()
    student_id = created["id"]

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()

    assert row is not None
    assert row["name"] == "Persistent Student"
    assert row["email"] == "persist@example.com"


def test_openapi_schema_has_distinct_operation_ids():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()

    # Collect all operation IDs in paths
    operation_ids = []
    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if isinstance(operation, dict) and "operationId" in operation:
                operation_ids.append(operation["operationId"])

    # Ensure no duplicates anywhere in OpenAPI schema
    assert len(operation_ids) == len(set(operation_ids))

    # Verify distinct operation IDs specifically for PUT and PATCH
    student_path = schema["paths"]["/students/{student_id}"]
    assert student_path["put"]["operationId"] == "update_student_put"
    assert student_path["patch"]["operationId"] == "update_student_patch"


def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "EWB Students CRUD API"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"
    assert data["students"] == "/students"


def test_health_endpoint():
    resp_initial = client.get("/health")
    assert resp_initial.status_code == 200
    assert resp_initial.json()["status"] == "ok"
    assert resp_initial.json()["students"] == 0

    _create()
    resp_after = client.get("/health")
    assert resp_after.status_code == 200
    assert resp_after.json()["students"] == 1


def test_filter_by_course_and_pagination():
    _create(name="CS Student 1", course="Computer Science")
    _create(name="CS Student 2", course="Computer Science")
    _create(name="Mech Student", course="Mechanical Engineering")

    # Filter by course substring
    cs_resp = client.get("/students", params={"course": "Computer"}).json()
    assert len(cs_resp) == 2
    assert all("Computer" in s["course"] for s in cs_resp)

    # Test pagination: limit
    limit_resp = client.get("/students", params={"limit": 2}).json()
    assert len(limit_resp) == 2

    # Test pagination: limit + offset
    offset_resp = client.get("/students", params={"limit": 2, "offset": 2}).json()
    assert len(offset_resp) == 1


def test_filter_born_before():
    _create(name="Older Student", date_of_birth="1999-05-10")
    _create(name="Younger Student", date_of_birth="2008-08-20")

    older_resp = client.get("/students", params={"born_before": "2005-01-01"}).json()
    assert len(older_resp) == 1
    assert older_resp[0]["name"] == "Older Student"


def test_ai_ask_unavailable_returns_503():
    # Safely mock network disconnection to Ollama without needing Ollama installed
    with patch("httpx.post", side_effect=httpx.ConnectError("Connection refused")):
        resp = client.post("/ai/ask", json={"question": "How many students are enrolled?"})
        assert resp.status_code == 503
        assert "Could not reach Ollama" in resp.json()["detail"]


def test_isolation_from_real_database():
    import os
    import sqlite3
    from app import database

    # Verify STUDENTS_DB points to an isolated temp path, NOT DEFAULT_DB_PATH
    active_test_db = os.environ.get("STUDENTS_DB")
    assert active_test_db is not None
    assert str(active_test_db) != str(database.DEFAULT_DB_PATH)

    # Verify the real production database file is not modified/truncated by test runs
    if database.DEFAULT_DB_PATH.exists():
        conn = sqlite3.connect(database.DEFAULT_DB_PATH)
        real_count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        conn.close()
        assert real_count == 8, f"Real database was modified! Expected 8 rows, got {real_count}"
