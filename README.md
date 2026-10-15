# EWB Students Database CRUD API

A Python backend that manages student records with full **C**reate / **R**ead /
**U**pdate / **D**elete operations, built for the **EWB Edu Tech internship
assignment**.

- **Framework:** FastAPI
- **Storage:** SQLite (persistent, local file)
- **Validation:** Pydantic
- **Optional bonus:** a local-AI endpoint (Ollama) that answers natural-language
  questions grounded in the stored data

> No cloud services, no API keys, no internet required. Everything runs locally.

---

## 1. Prerequisites

- **Python 3.10+** (`python --version`)
- `pip` (comes with Python)
- *(optional, for the AI bonus only)* [Ollama](https://ollama.com/download)

SQLite needs **no installation** — it ships with Python's standard library.

---

## 2. Installation

```bash
# 1. Go to the project folder
cd ewb-students-crud

# 2. Create and activate a virtual environment
python -m venv .venv

# Activate it:
#   Git Bash (Windows):   source .venv/Scripts/activate
#   PowerShell (Windows): .venv\Scripts\Activate.ps1
#   macOS / Linux:        source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 3. Run the server

```bash
uvicorn app.main:app --reload
```

Then open:

- **Swagger UI (interactive docs & testing):** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Health check:** http://localhost:8000/health

The database file `students.db` is created automatically on first run.

### Load sample data (optional but recommended for a demo)

```bash
python seed.py          # inserts 8 dummy students (only if DB is empty)
python seed.py --reset  # wipes and re-inserts
```

> All sample data is fake — no real student information is included or committed.

---

## 4. API endpoints

| Method       | Endpoint                 | Purpose                 |
| ------------ | ------------------------ | ----------------------- |
| `POST`       | `/students`              | Create a student        |
| `GET`        | `/students`              | List / filter students  |
| `GET`        | `/students/{student_id}` | View a single student   |
| `PUT`/`PATCH`| `/students/{student_id}` | Update a student        |
| `DELETE`     | `/students/{student_id}` | Delete a student        |
| `POST`       | `/ai/ask`                | *(optional)* Ask the AI |

### Student fields

| Field             | Type   | Required | Notes                                   |
| ----------------- | ------ | -------- | --------------------------------------- |
| `id`              | int    | auto     | Unique primary key                      |
| `name`            | string | ✅       | Non-empty                               |
| `date_of_birth`   | date   | ✅       | `YYYY-MM-DD`, must be in the past       |
| `email`           | string | ⚠️       | Valid email; **email or phone** required |
| `phone`           | string | ⚠️       | **email or phone** required             |
| `course`          | string | –        | Optional                                |
| `address`         | string | –        | Optional                                |
| `enrollment_date` | date   | –        | Optional, `YYYY-MM-DD`                  |

### List filters (query parameters on `GET /students`)

| Param         | Example                 | Meaning                           |
| ------------- | ----------------------- | --------------------------------- |
| `search`      | `?search=asha`          | Partial, case-insensitive name    |
| `course`      | `?course=Computer`      | Partial course match              |
| `born_after`  | `?born_after=2005-01-01`| DOB strictly after the date       |
| `born_before` | `?born_before=2005-01-01`| DOB strictly before the date     |
| `limit`       | `?limit=10`             | Max rows (1–1000, default 100)    |
| `offset`      | `?offset=20`            | Skip N rows (pagination)          |

---

## 5. Testing the API

### Option A — Swagger UI (easiest)
Open http://localhost:8000/docs and click **Try it out** on any endpoint.

### Option B — `requests.http`
Open [`requests.http`](requests.http) in VS Code (REST Client extension) or a
JetBrains IDE and click **Send Request**.

### Option C — curl

```bash
# Create
curl -X POST http://localhost:8000/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Asha Verma","date_of_birth":"2004-06-15","email":"asha@example.com","course":"CS"}'

# List + filter
curl "http://localhost:8000/students?born_after=2005-01-01"

# View one
curl http://localhost:8000/students/1

# Update (partial)
curl -X PATCH http://localhost:8000/students/1 \
  -H "Content-Type: application/json" \
  -d '{"course":"Data Science"}'

# Delete
curl -X DELETE http://localhost:8000/students/1
```

### Automated tests

```bash
pytest -v
```

Tests run against a temporary database, so your real `students.db` is untouched.

---

## 6. Optional bonus: local AI with Ollama

The core app is complete without this. To enable natural-language questions:

```bash
# 1. Install Ollama from https://ollama.com, then pull a small model
ollama pull llama3.2:1b

# 2. Make sure Ollama is running (it usually runs as a background service),
#    or start it manually:
ollama serve

# 3. Make sure you have some data
python seed.py

# 4. Ask a question
curl -X POST http://localhost:8000/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"How many students are there, and who was born after 2005?"}'
```

**How it stays safe & accurate:** the backend fetches the relevant records from
SQLite *in Python*, then passes them to the model as read-only context. The model
**never** executes SQL or touches the database — it only summarises the data we
hand it. If Ollama isn't running, the endpoint returns a clear `503` and the rest
of the API keeps working.

Configuration (optional, via environment variables):

| Variable       | Default                  |
| -------------- | ------------------------ |
| `OLLAMA_URL`   | `http://localhost:11434` |
| `OLLAMA_MODEL` | `llama3.2:1b`            |

---

## 7. Project structure

```
ewb-students-crud/
├── app/
│   ├── __init__.py
│   ├── main.py        # FastAPI app + all endpoints
│   ├── database.py    # SQLite connection + table setup
│   ├── schemas.py     # Pydantic models (validation + responses)
│   ├── crud.py        # Parameterised DB operations
│   └── ai.py          # Optional Ollama integration
├── tests/
│   ├── conftest.py
│   └── test_students.py
├── seed.py            # Dummy data loader
├── requirements.txt
├── requests.http      # Ready-to-run sample requests
├── .gitignore
└── README.md
```

---

## 8. Notes

- Validation and 404 handling are built in: invalid payloads return `422`,
  unknown IDs return `404`.
- SQL injection is avoided throughout — **every** query is parameterised.
- Do not commit `students.db`, secrets, or real personal data (`.gitignore`
  already excludes the database and `.env`).
