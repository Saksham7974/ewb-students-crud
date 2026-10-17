"""Data-access layer: all SQLite reads/writes live here.

Keeping SQL in one place makes the API handlers thin and keeps the security
property easy to verify: **every** query below is parameterised (``?``
placeholders), so values are never concatenated into SQL.
"""
from __future__ import annotations

from datetime import date
import sqlite3
from typing import Any, Optional

from . import database
from .schemas import StudentCreate, StudentUpdate

# Columns a client is allowed to update. Used to whitelist dynamic UPDATE keys.
_UPDATABLE = {
    "name",
    "date_of_birth",
    "email",
    "phone",
    "course",
    "address",
    "enrollment_date",
}


def _to_db(value: Any) -> Any:
    """Convert Python values to what SQLite should store."""
    if isinstance(value, date):
        return value.isoformat()
    return value


def create_student(data: StudentCreate) -> dict:
    with database.get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO students
                    (name, date_of_birth, email, phone, course, address, enrollment_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.name,
                    data.date_of_birth.isoformat(),
                    data.email,
                    data.phone,
                    data.course,
                    data.address,
                    _to_db(data.enrollment_date),
                ),
            )
        except sqlite3.IntegrityError:
            raise ValueError(f"A student with email '{data.email}' already exists.")
        # Read back on the SAME connection so we see the uncommitted row.
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)


def get_student(student_id: int) -> Optional[dict]:
    with database.get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        return dict(row) if row else None


def get_student_by_email(
    email: str, exclude_id: Optional[int] = None
) -> Optional[dict]:
    query = "SELECT * FROM students WHERE lower(email) = lower(?)"
    params: list[Any] = [email]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    query += " LIMIT 1"

    with database.get_connection() as conn:
        row = conn.execute(query, params).fetchone()
        return dict(row) if row else None


def list_students(
    search: Optional[str] = None,
    course: Optional[str] = None,
    born_after: Optional[date] = None,
    born_before: Optional[date] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    clauses: list[str] = []
    params: list[Any] = []

    if search:
        clauses.append("name LIKE ?")
        params.append(f"%{search}%")
    if course:
        clauses.append("course LIKE ?")
        params.append(f"%{course}%")
    if born_after:
        clauses.append("date_of_birth > ?")
        params.append(born_after.isoformat())
    if born_before:
        clauses.append("date_of_birth < ?")
        params.append(born_before.isoformat())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.extend([limit, offset])

    with database.get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM students {where} ORDER BY id LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        return [dict(r) for r in rows]


def update_student(student_id: int, data: StudentUpdate) -> Optional[dict]:
    # Only the fields the client actually sent (PATCH-style partial update).
    fields = data.model_dump(exclude_unset=True)
    # Keys are restricted to a fixed whitelist, so building the SET clause by
    # name is safe; all values stay parameterised.
    sets, params = [], []
    for key, value in fields.items():
        if key not in _UPDATABLE:
            continue
        sets.append(f"{key} = ?")
        params.append(_to_db(value))

    with database.get_connection() as conn:
        if sets:
            params.append(student_id)
            try:
                conn.execute(
                    f"UPDATE students SET {', '.join(sets)} WHERE id = ?", params
                )
            except sqlite3.IntegrityError:
                raise ValueError(
                    f"A student with email '{fields.get('email')}' already exists."
                )
        row = conn.execute(
            "SELECT * FROM students WHERE id = ?", (student_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_student(student_id: int) -> bool:
    with database.get_connection() as conn:
        cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
        return cur.rowcount > 0


def count_students() -> int:
    with database.get_connection() as conn:
        return conn.execute("SELECT COUNT(*) AS n FROM students").fetchone()["n"]
