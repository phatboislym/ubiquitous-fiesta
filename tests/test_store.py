"""Unit tests for TaskStore, with the clock pinned so timestamps are exact."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from app.models import TaskCreate, TaskUpdate
from app.store import TaskStore

T0 = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
T1 = T0 + timedelta(hours=1)
T2 = T0 + timedelta(hours=2)


@pytest.fixture
def set_now(monkeypatch: pytest.MonkeyPatch) -> Callable[[datetime], None]:
    """Call set_now(t) to make the store's clock return t until the next call."""

    def set_now(when: datetime) -> None:
        monkeypatch.setattr("app.store._now", lambda: when)

    return set_now


def test_create_sets_both_timestamps(
    store: TaskStore, set_now: Callable[[datetime], None]
) -> None:
    set_now(T0)
    task = store.create(TaskCreate(title="New"))

    assert task.created_at == T0
    assert task.updated_at == T0
    assert task.completed_at is None


def test_update_bumps_updated_at_only(
    store: TaskStore, set_now: Callable[[datetime], None]
) -> None:
    set_now(T0)
    task = store.create(TaskCreate(title="Old"))
    set_now(T1)
    updated = store.update(task.id, TaskUpdate(title="New"))

    assert updated is not None
    assert updated.title == "New"
    assert updated.created_at == T0
    assert updated.updated_at == T1


def test_update_is_saved(store: TaskStore) -> None:
    task = store.create(TaskCreate(title="Old"))
    store.update(task.id, TaskUpdate(title="New"))

    saved = store.get(task.id)
    assert saved is not None
    assert saved.title == "New"


def test_complete_records_when(
    store: TaskStore, set_now: Callable[[datetime], None]
) -> None:
    set_now(T0)
    task = store.create(TaskCreate(title="Do it"))
    set_now(T1)
    completed = store.complete(task.id)

    assert completed is not None
    assert completed.completed is True
    assert completed.completed_at == T1
    assert completed.updated_at == T1


def test_complete_twice_keeps_the_first_time(
    store: TaskStore, set_now: Callable[[datetime], None]
) -> None:
    set_now(T0)
    task = store.create(TaskCreate(title="Do it"))
    set_now(T1)
    store.complete(task.id)
    set_now(T2)
    again = store.complete(task.id)

    assert again is not None
    assert again.completed_at == T1
    assert again.updated_at == T1


def test_delete_reports_whether_the_task_existed(store: TaskStore) -> None:
    task = store.create(TaskCreate(title="Bye"))

    assert store.delete(task.id) is True
    assert store.delete(task.id) is False
    assert store.get(task.id) is None


def test_ids_are_not_reused_after_delete(store: TaskStore) -> None:
    first = store.create(TaskCreate(title="One"))
    store.delete(first.id)

    assert store.create(TaskCreate(title="Two")).id == first.id + 1


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda s: s.get(999), id="get"),
        pytest.param(lambda s: s.update(999, TaskUpdate(title="x")), id="update"),
        pytest.param(lambda s: s.complete(999), id="complete"),
    ],
)
def test_missing_task_returns_none(
    store: TaskStore, call: Callable[[TaskStore], object]
) -> None:
    assert call(store) is None
