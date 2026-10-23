from collections.abc import Iterable
from datetime import UTC, datetime
from itertools import count

from app.models import Task, TaskCreate, TaskUpdate


def _now() -> datetime:
    return datetime.now(UTC)


class TaskStore:
    """In-memory task repository. All data is lost when the process restarts.

    Methods return None (or False) when a task doesn't exist; the route layer
    decides how to turn that into a 404.
    """

    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}
        self._ids = count(1)

    def create(self, data: TaskCreate) -> Task:
        now = _now()
        task = Task(
            id=next(self._ids),
            **data.model_dump(),
            completed=False,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task.id] = task
        return task

    def get(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

    def list_all(self, completed: bool | None = None) -> list[Task]:
        tasks: Iterable[Task] = self._tasks.values()
        if completed is not None:
            tasks = (t for t in tasks if t.completed == completed)
        return sorted(tasks, key=lambda t: t.id, reverse=True)  # newest first

    def update(self, task_id: int, data: TaskUpdate) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        # exclude_unset => PATCH semantics: only fields the client sends
        changes = data.model_dump(exclude_unset=True)
        updated = task.model_copy(update={**changes, "updated_at": _now()})
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None

    def complete(self, task_id: int) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None or task.completed:
            # missing -> None; already completed -> unchanged (idempotent)
            return task
        now = _now()
        completed = task.model_copy(
            update={"completed": True, "completed_at": now, "updated_at": now}
        )
        self._tasks[task_id] = completed
        return completed


_store = TaskStore()


def get_store() -> TaskStore:
    """FastAPI dependency. Tests can swap it with app.dependency_overrides."""
    return _store
