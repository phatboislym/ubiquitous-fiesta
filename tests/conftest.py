import pytest
from fastapi.testclient import TestClient

from app import main
from app.store import TaskStore


@pytest.fixture
def store() -> TaskStore:
    """A fresh, empty store, so tests never see each other's tasks."""
    return TaskStore()


@pytest.fixture
def client(store: TaskStore, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A test client whose routes use the `store` fixture instead of the real one."""
    # Routes look up main.store on every call, so replacing the module attribute
    # is enough. monkeypatch puts the real store back after the test.
    monkeypatch.setattr(main, "store", store)
    return TestClient(main.app)
