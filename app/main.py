"""FastAPI application: the REST API for managing student records.

Run it with:  uvicorn app.main:app --reload
Interactive docs:  http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, status

from . import crud, database
from .schemas import AskRequest, Student, StudentCreate, StudentUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure the table exists before serving any request.
    database.init_db()
    yield


app = FastAPI(
    title="EWB Students CRUD API",
    version="1.0.0",
    description=(
        "A Students Database CRUD application built with FastAPI + SQLite for the "
        "EWB Edu Tech internship assignment. Includes an optional local-AI "
        "(Ollama) endpoint that answers questions grounded in the stored data."
    ),
    lifespan=lifespan,
)


# --------------------------------------------------------------------------- #
# Meta / health
# --------------------------------------------------------------------------- #
@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "EWB Students CRUD API",
        "docs": "/docs",
        "health": "/health",
        "students": "/students",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "students": crud.count_students()}


# --------------------------------------------------------------------------- #
# CRUD: students
# --------------------------------------------------------------------------- #
@app.post(
    "/students",
    response_model=Student,
    status_code=status.HTTP_201_CREATED,
    tags=["students"],
    summary="Create a student",
)
def create_student(payload: StudentCreate) -> dict:
    if payload.email:
        duplicate = crud.get_student_by_email(payload.email)
        if duplicate:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"A student with email '{payload.email}' already exists.",
            )
    try:
        return crud.create_student(payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@app.get(
    "/students",
    response_model=list[Student],
    tags=["students"],
    summary="List / filter students",
)
def list_students(
    search: Optional[str] = Query(None, description="Partial, case-insensitive name match"),
    course: Optional[str] = Query(None, description="Partial course match"),
    born_after: Optional[date] = Query(None, description="Only students born after this date (YYYY-MM-DD)"),
    born_before: Optional[date] = Query(None, description="Only students born before this date (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return crud.list_students(
        search=search,
        course=course,
        born_after=born_after,
        born_before=born_before,
        limit=limit,
        offset=offset,
    )


@app.get(
    "/students/{student_id}",
    response_model=Student,
    tags=["students"],
    summary="View a single student",
)
def get_student(student_id: int) -> dict:
    student = crud.get_student(student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    return student


def _handle_update_student(student_id: int, payload: StudentUpdate) -> dict:
    existing = crud.get_student(student_id)
    if existing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")

    changes = payload.model_dump(exclude_unset=True)

    # Check email uniqueness if email is being updated to a non-null address
    if "email" in changes and changes["email"]:
        duplicate = crud.get_student_by_email(
            changes["email"], exclude_id=student_id
        )
        if duplicate:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"A student with email '{changes['email']}' already exists.",
            )

    # Enforce the "at least one contact" rule against the merged result.
    final_email = changes["email"] if "email" in changes else existing["email"]
    final_phone = changes["phone"] if "phone" in changes else existing["phone"]
    if not final_email and not final_phone:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Student must keep at least one contact (email or phone)",
        )

    try:
        return crud.update_student(student_id, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))


@app.put(
    "/students/{student_id}",
    response_model=Student,
    tags=["students"],
    summary="Update a student (PUT)",
    operation_id="update_student_put",
)
def update_student_put(student_id: int, payload: StudentUpdate) -> dict:
    return _handle_update_student(student_id, payload)


@app.patch(
    "/students/{student_id}",
    response_model=Student,
    tags=["students"],
    summary="Update a student (PATCH - partial update)",
    operation_id="update_student_patch",
)
def update_student_patch(student_id: int, payload: StudentUpdate) -> dict:
    return _handle_update_student(student_id, payload)


@app.delete(
    "/students/{student_id}",
    tags=["students"],
    summary="Delete a student",
)
def delete_student(student_id: int) -> dict:
    if not crud.delete_student(student_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found")
    return {"message": "Student deleted", "id": student_id}


# --------------------------------------------------------------------------- #
# Optional bonus: local AI (Ollama)
# --------------------------------------------------------------------------- #
@app.post(
    "/ai/ask",
    tags=["ai (optional)"],
    summary="Ask a natural-language question about the students",
)
def ai_ask(payload: AskRequest) -> dict:
    from .ai import OllamaUnavailable, ask

    try:
        return ask(payload.question)
    except OllamaUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
