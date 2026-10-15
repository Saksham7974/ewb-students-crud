"""Optional local-AI extension (the assignment's bonus section).

Flow (RAG-style, fully grounded):
    1. Fetch the relevant records from SQLite in *Python* (never the model).
    2. Pass them to a locally running Ollama model as read-only context.
    3. Return the model's answer.

Security: the model only ever sees text we hand it. It cannot run SQL or touch
the database, which satisfies the "do not let the model execute unrestricted
SQL" requirement.

This whole module is optional — the core CRUD API works without Ollama or even
without ``httpx`` installed.
"""
from __future__ import annotations

import os

from . import crud

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")

SYSTEM_PROMPT = (
    "You are an assistant for a student-records system. "
    "Answer the user's question using ONLY the student data provided below. "
    "If the answer is not contained in the data, say you do not have that "
    "information. Never invent students. Be concise.\n\n"
)


class OllamaUnavailable(RuntimeError):
    """Raised when the local Ollama server cannot be reached."""


def _build_context() -> tuple[str, int]:
    """Return (context_text, number_of_records) from the database."""
    students = crud.list_students(limit=1000)
    if not students:
        return "(no students in the database)", 0
    lines = [
        "id={id} | name={name} | dob={date_of_birth} | email={email} | "
        "phone={phone} | course={course} | enrollment_date={enrollment_date}".format(
            **{k: ("" if v is None else v) for k, v in s.items()}
        )
        for s in students
    ]
    return "\n".join(lines), len(students)


def ask(question: str) -> dict:
    """Answer a natural-language question grounded in the stored records."""
    # Import httpx lazily so the core app never hard-depends on it.
    try:
        import httpx
    except ImportError as exc:  # pragma: no cover - env specific
        raise OllamaUnavailable(
            "The 'httpx' package is required for the AI endpoint. "
            "Install it with: pip install httpx"
        ) from exc

    context, considered = _build_context()
    prompt = f"{SYSTEM_PROMPT}STUDENT DATA:\n{context}\n\nQUESTION: {question}"

    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(
            f"Could not reach Ollama at {OLLAMA_URL}. Is it running? "
            "Start it with 'ollama serve' and 'ollama pull " + OLLAMA_MODEL + "'."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaUnavailable(
            f"Ollama returned an error ({exc.response.status_code}). "
            f"Is the model '{OLLAMA_MODEL}' pulled? Try: ollama pull {OLLAMA_MODEL}"
        ) from exc

    data = resp.json()
    return {
        "question": question,
        "answer": (data.get("response") or "").strip(),
        "model": OLLAMA_MODEL,
        "students_considered": considered,
    }
