# Tasker API

a small REST API for managing tasks, built with [FastAPI](https://fastapi.tiangolo.com/) and [uv](https://docs.astral.sh/uv/).

this project is a progressive exercise. it starts as a flat, in-memory CRUD app and grows, one stage at a time, into a versioned, tested, production-ready service (see the [Roadmap](#roadmap)).

## Features

- create, list, view, update, and delete tasks
- mark a task as completed
- pagination with `page` / `page_size`, returned as a `PagedResult` object
- URI-based API versioning (`/v1`, `/v2`)
- interactive API docs (Swagger UI) generated automatically from the code

**out of scope:** frontend UI, notifications, sharing or collaboration, recurring tasks, file attachments.

## Tech Stack

| Purpose                  | Tool                                                    |
| ------------------------ | ------------------------------------------------------- |
| web framework            | FastAPI (with `fastapi[standard]`: uvicorn, CLI, httpx) |
| validation / schemas     | Pydantic                                                |
| package & env management | uv                                                      |
| testing                  | pytest                                                  |
| linting & formatting     | ruff                                                    |
| type checking            | mypy (strict, with the Pydantic plugin)                 |

## Getting Started

**prerequisite:** [install uv](https://docs.astral.sh/uv/getting-started/installation/). uv also manages the Python version (pinned in `.python-version`).

```bash
git clone <repo-url>
cd task-api
uv sync                              # creates .venv and installs locked dependencies
uv run fastapi dev app/main.py       # dev server with auto-reload
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

run the tests:

```bash
uv run pytest
```

lint, format, and type-check (configured in `pyproject.toml`):

```bash
uv run ruff check .                  # lint
uv run ruff format .                 # format in place
uv run mypy app tests                # strict type check
```

### Bootstrapping from scratch

if you are recreating the project rather than cloning it:

```bash
uv init task-api --bare --pin-python --vcs git
cd task-api
uv add "fastapi[standard]"
uv add --dev pytest ruff mypy

mkdir app tests
touch app/__init__.py app/main.py app/models.py app/store.py
```

commit `uv.lock` so everyone gets identical dependency versions.

## API Reference

all endpoints live under a version prefix (`/v1`, later `/v2`).

| Action            | Method & Path                  | Success response     |
| ----------------- | ------------------------------ | -------------------- |
| create a task     | `POST /v1/tasks`               | `201` + created task |
| list tasks        | `GET /v1/tasks`                | `200` + tasks        |
| get one task      | `GET /v1/tasks/{id}`           | `200` + task         |
| update a task     | `PATCH /v1/tasks/{id}`         | `200` + updated task |
| delete a task     | `DELETE /v1/tasks/{id}`        | `204` no content     |
| mark as completed | `POST /v1/tasks/{id}/complete` | `200` + updated task |

**update:** `PATCH` is a partial update. clients send only the fields they want to change.

**complete:** sets `completed = true` and records `completed_at`. it is idempotent, so completing an already-completed task changes nothing and still succeeds.

**list filters:** `?completed=true|false`. results are sorted newest first by default.

### Data model

JSON field names are camelCase, the Python models use snake_case and convert automatically

| Field         | Type            | Notes                          |
| ------------- | --------------- | ------------------------------ |
| `id`          | integer         | primary key                    |
| `title`       | string          | required, 1–256 characters     |
| `description` | string          | optional, max ~2048 characters |
| `completed`   | boolean         | defaults to `false`            |
| `dueDate`     | date / datetime | optional                       |
| `createdAt`   | timestamp       | set automatically              |
| `updatedAt`   | timestamp       | updated on every change        |
| `completedAt` | timestamp       | null until completed           |

### Errors

errors share one JSON shape:

```json
{ "error": { "code": "NOT_FOUND", "message": "Task 42 not found" } }
```

| Status | Meaning                                                                                 |
| ------ | --------------------------------------------------------------------------------------- |
| `404`  | task does not exist (get, update, delete, complete)                                     |
| `422`  | request validation failed (FastAPI's default; override the handler if you prefer `400`) |
| `500`  | unexpected server error                                                                 |

## Pagination

list endpoints use offset-based pagination with `page` and `pageSize`:

```
GET /v2/tasks?page=3&page_size=20
```

The server computes `limit = pageSize` and `offset = (page - 1) * pageSize`.

Responses are wrapped in a generic `PagedResult[T]`:

```json
{
  "data": [{ "id": 41, "title": "Write README", "completed": false }],
  "total": 235,
  "page": 3,
  "pageSize": 20,
  "totalPages": 12
}
```

Rules:

- defaults: `page=1`, `pageSize=20`
- `pageSize` is capped (100) so a single call cannot return a large table
- `page < 1` or `pageSize < 1` is rejected as a validation error
- a page past the end returns `200` with an empty `data` array and the real `total`, not a `404`
- with no results, `totalPages` is `0`
- `totalPages` is derived from `total` and `pageSize` in one place so the fields cannot drift apart

offset pagination is the right fit at this scale. cursor-based pagination is a possible later upgrade for larger datasets.

## Versioning

the API uses **URI path versioning** (`/v1/tasks`), because it is the simplest to implement, test, and demonstrate. `/v1` is present from day one, since retrofitting a version prefix later is itself a breaking change.

- **bump the version only for breaking changes:** removing or renaming a field, changing a type, or changing a response shape. adding an optional field or a new endpoint is not breaking.
- **version the HTTP layer, not the whole app.** domain logic and storage are shared. each version has its own router and request/response schemas.

|            | `GET /v1/tasks`      | `GET /v2/tasks`     |
| ---------- | -------------------- | ------------------- |
| response   | plain array of tasks | `PagedResult[Task]` |
| pagination | None                 | `page` / `pageSize` |

wrapping an array in an object breaks existing clients, which makes it the first real breaking change in this project.

**deprecation:** once `/v2` ships, `/v1` is not removed immediately. it gains `Deprecation` and `Sunset` response headers, usage is logged, and a retirement date is set.

## Project Structure

**Stage 1 (flat):**

```
app/
  main.py        # FastAPI app, /v1 router, all endpoints
  models.py      # Pydantic models: Task, TaskCreate, TaskUpdate, PagedResult[T]
  store.py       # in-memory repository
tests/
  test_tasks.py
```

**target (later stages):** the flat layout splits as the exercises introduce each concern.

```
app/
  main.py                  # app factory, mounts /v1 and /v2 routers
  config.py                # validated environment settings
  domain/
    models.py              # Task, PagedResult[T]
    service.py             # business logic, shared by all versions
    repository.py          # repository interface
    errors.py              # NotFoundError, etc.
  infrastructure/
    db/                    # concrete repository (SQLite / Postgres)
  api/
    shared/                # pagination params, error handlers, deprecation headers
    v1/                    # APIRouter(prefix="/v1"), schemas, mapper
    v2/                    # APIRouter(prefix="/v2"), schemas, mapper
tests/
  v1/
  v2/
```

services raise domain errors (e.g. `NotFoundError`) and a shared handler converts them to HTTP responses, which keeps HTTP concerns out of the domain layer.

## Roadmap

- [ ] **Stage 1: Core CRUD.** in-memory store, `/v1` endpoints, complete action, basic health check, Swagger docs.
- [ ] **Stage 2: Validation & errors.** field constraints, consistent error shape, correct status codes.
- [ ] **Stage 3: Persistence & config.** SQLite, repository interface, environment-based settings, no hardcoded secrets.
- [ ] **Stage 4: Layering.** extract a service layer, per-version routers, and DTO mapping.
- [ ] **Stage 5: Pagination & `/v2`.** introduce `PagedResult[T]` as a breaking change, so `/v2` is born.
- [ ] **Stage 6: Testing.** unit tests for logic, integration tests for every endpoint including failure cases.
- [ ] **Stage 7: Deprecation.** `Deprecation` / `Sunset` headers on `/v1`, usage logging, retirement.
- [ ] **Stage 8: Production hardening.** authentication, structured logging, robust health checks, Docker, CI.

## Acceptance Criteria

- every endpoint returns the documented status codes and JSON shapes.
- invalid input never creates or corrupts data.
- getting, updating, or deleting a nonexistent ID returns `404`.
- completing a task sets `completedAt`, and repeating the call changes nothing.
- all tests pass, and the service starts from a fresh clone using only the steps in this README.

## Open Decisions

1. **authentication:** single-user and open, or per-user tasks (JWT or API keys)? this is the biggest scope driver.
2. **reopening tasks:** should a completed task be reopenable? If so, `PATCH` with `completed: false` is the simplest route.
3. **delete style:** hard delete, or soft delete with a `deleted_at` flag?
4. **extras:** priority, tags, or search in v1, or core CRUD only?
