"""Populate the database with dummy students for demos and testing.

All data here is fake. Run once:  python seed.py
Use --reset to wipe existing rows first:  python seed.py --reset
"""
from __future__ import annotations

import sys

from app import crud, database
from app.schemas import StudentCreate

# Dummy records. Birth years deliberately span before/after 2005 so the AI demo
# question "List students born after 2005" has something to work with.
SAMPLE_STUDENTS = [
    {"name": "Asha Verma", "date_of_birth": "2004-06-15", "email": "asha.verma@example.com", "phone": "+91 98765 43210", "course": "Computer Science", "address": "Pune", "enrollment_date": "2022-08-01"},
    {"name": "Rahul Nair", "date_of_birth": "2006-01-22", "email": "rahul.nair@example.com", "phone": "+91 90000 11111", "course": "Mechanical Engineering", "address": "Kochi", "enrollment_date": "2023-07-15"},
    {"name": "Meera Iyer", "date_of_birth": "2003-11-09", "email": "meera.iyer@example.com", "course": "Data Science", "address": "Chennai", "enrollment_date": "2021-09-01"},
    {"name": "Dev Sharma", "date_of_birth": "2007-03-30", "phone": "+91 91234 56780", "course": "Computer Science", "address": "Delhi", "enrollment_date": "2024-08-05"},
    {"name": "Fatima Khan", "date_of_birth": "2005-07-18", "email": "fatima.khan@example.com", "phone": "+91 99887 76655", "course": "Electronics", "address": "Hyderabad", "enrollment_date": "2023-08-10"},
    {"name": "John Dsouza", "date_of_birth": "2002-12-01", "email": "john.dsouza@example.com", "course": "Civil Engineering", "address": "Goa", "enrollment_date": "2020-07-20"},
    {"name": "Priya Patel", "date_of_birth": "2006-09-14", "email": "priya.patel@example.com", "phone": "+91 93333 22211", "course": "Data Science", "address": "Ahmedabad", "enrollment_date": "2024-07-01"},
    {"name": "Arjun Reddy", "date_of_birth": "2008-02-05", "email": "arjun.reddy@example.com", "course": "Computer Science", "address": "Bengaluru", "enrollment_date": "2025-08-01"},
]


def seed(reset: bool = False) -> None:
    database.init_db()

    if reset:
        # Simple wipe for a clean demo run.
        with database.get_connection() as conn:
            conn.execute("DELETE FROM students")
        print("Existing students removed.")

    if crud.count_students() > 0 and not reset:
        print(
            f"Database already has {crud.count_students()} students; "
            "nothing inserted. Use --reset to reseed."
        )
        return

    for record in SAMPLE_STUDENTS:
        crud.create_student(StudentCreate(**record))

    print(f"Inserted {len(SAMPLE_STUDENTS)} dummy students. Total: {crud.count_students()}")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
