"""Pytest configuration.

Point the app at a throwaway SQLite file *before* the app is imported, so tests
never touch your real ``students.db``.
"""
import os
import pathlib
import tempfile

import pytest

_TMP_DIR = tempfile.mkdtemp(prefix="ewb_students_test_")
os.environ["STUDENTS_DB"] = str(pathlib.Path(_TMP_DIR) / "test_students.db")


@pytest.fixture(autouse=True)
def _clean_db():
    """Start every test with an empty students table."""
    from app import database

    database.init_db()
    with database.get_connection() as conn:
        conn.execute("DELETE FROM students")
    yield
