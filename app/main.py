from fastapi import FastAPI

from app.models import Task, TaskCreate, TaskUpdate
from app.store import get_store

app = FastAPI(title="Tasker API")
store = get_store()


@app.get("/")
def home() -> dict[str, str]:
    """Return a welcome message."""
    return {"message": "Welcome to Tasker"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check: returns {"status": "ok"} while the app is running."""
    return {"status": "ok"}


@app.post("/tasks")
def create(data: TaskCreate) -> Task:
    """Create a task. New tasks start uncompleted and get the next free id."""
    return store.create(data)


@app.get("/tasks")
def _list(completed: bool | None = None) -> list[Task]:
    """List tasks, newest first. Pass `completed` to filter by completion status."""
    return store.list_all(completed)


@app.get("/tasks/{id}")
def get(id: int) -> Task | None:
    """Fetch one task by id, or null if no task has that id."""
    return store.get(id)


@app.patch("/tasks/{id}")
def update(id: int, data: TaskUpdate) -> Task | None:
    """Partially update a task: only the fields sent in the body are changed.

    Returns the updated task, or null if no task has that id.
    """
    return store.update(id, data)


@app.delete("/tasks/{id}")
def delete(id: int) -> bool:
    """Delete a task. Returns true if it existed, false otherwise."""
    return store.delete(id)


@app.post("/tasks/{id}/complete")
def complete(id: int) -> Task | None:
    return store.complete(id)
