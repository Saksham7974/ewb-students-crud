"""SQLite database helpers.

We use the standard-library ``sqlite3`` module (no ORM) so the data layer stays
small, transparent and easy to demo. Every query is parameterised, so user input
is never interpolated into SQL strings.
"""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# Default database file lives next to the project root. The path can be
# overridden with the STUDENTS_DB environment variable (used by the tests so
# they never touch your real data).
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "students.db"


def _db_path() -> str:
    path = Path(os.environ.get("STUDENTS_DB", str(DEFAULT_DB_PATH)))
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a SQLite connection, committing on success and always closing.

    ``sqlite3.Connection`` used as a plain context manager only manages the
    transaction (it does not close the connection), so we wrap it ourselves to
    avoid leaking file handles.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create the ``students`` table and unique index if they do not exist yet."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL,
                date_of_birth   TEXT    NOT NULL,          -- ISO 8601 (YYYY-MM-DD)
                email           TEXT,
                phone           TEXT,
                course          TEXT,
                address         TEXT,
                enrollment_date TEXT,                      -- ISO 8601 (YYYY-MM-DD)
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        # Create unique index on non-null lowercased email, handling legacy duplicates safely
        try:
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_students_email_unique
                ON students(lower(email))
                WHERE email IS NOT NULL AND email != ''
                """
            )
        except sqlite3.OperationalError:
            # If pre-existing duplicate records already exist in an old DB, do not abort;
            # application-level checks in crud.py / main.py still protect new writes.
            pass
