"""HTTP-level tests: every endpoint, through FastAPI, against a fresh store."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.models import DESCRIPTION_MAX_LENGTH, TITLE_MAX_LENGTH


def create_task(client: TestClient, **fields: Any) -> dict[str, Any]:
    response = client.post("/v1/tasks", json={"title": "A task", **fields})
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# --- create ---


def test_create_returns_the_new_task(client: TestClient) -> None:
    task = create_task(client, title="Write tests")

    assert task["id"] == 1
    assert task["title"] == "Write tests"
    assert task["description"] is None
    assert task["dueDate"] is None
    assert task["completed"] is False
    assert task["completedAt"] is None
    assert task["createdAt"] == task["updatedAt"]


def test_create_accepts_optional_fields(client: TestClient) -> None:
    response = client.post(
        "/v1/tasks",
        json={
            "title": "Ship it",
            "description": "Stage 1",
            "dueDate": "2026-11-01T09:00:00Z",
        },
    )

    task = response.json()
    assert task["description"] == "Stage 1"
    assert task["dueDate"] == "2026-11-01T09:00:00Z"


def test_create_strips_whitespace_from_title(client: TestClient) -> None:
    assert create_task(client, title="  padded  ")["title"] == "padded"


def test_create_accepts_title_at_max_length(client: TestClient) -> None:
    title = "x" * TITLE_MAX_LENGTH
    assert create_task(client, title=title)["title"] == title


def test_create_gives_each_task_a_new_id(client: TestClient) -> None:
    ids = [create_task(client)["id"] for _ in range(3)]
    assert ids == [1, 2, 3]


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="missing-title"),
        pytest.param({"title": ""}, id="empty-title"),
        pytest.param({"title": "   "}, id="blank-title"),
        pytest.param({"title": "x" * (TITLE_MAX_LENGTH + 1)}, id="title-too-long"),
        pytest.param(
            {"title": "ok", "description": "x" * (DESCRIPTION_MAX_LENGTH + 1)},
            id="description-too-long",
        ),
        pytest.param({"title": "ok", "dueDate": "someday"}, id="bad-due-date"),
        pytest.param({"title": "ok", "completed": True}, id="unknown-field"),
    ],
)
def test_create_rejects_invalid_body(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post("/v1/tasks", json=body)

    assert response.status_code == 422
    # invalid input never creates data
    assert client.get("/v1/tasks").json() == []


# --- list ---


def test_list_is_empty_with_no_tasks(client: TestClient) -> None:
    assert client.get("/v1/tasks").json() == []


def test_list_returns_newest_first(client: TestClient) -> None:
    for title in ["first", "second", "third"]:
        create_task(client, title=title)

    titles = [task["title"] for task in client.get("/v1/tasks").json()]
    assert titles == ["third", "second", "first"]


def test_list_filters_by_completed(client: TestClient) -> None:
    for _ in range(3):
        create_task(client)
    client.post("/v1/tasks/2/complete")

    done = client.get("/v1/tasks", params={"completed": True}).json()
    not_done = client.get("/v1/tasks", params={"completed": False}).json()

    assert [task["id"] for task in done] == [2]
    assert [task["id"] for task in not_done] == [3, 1]


# --- get ---


def test_get_returns_the_task(client: TestClient) -> None:
    task = create_task(client, title="Find me")
    assert client.get(f"/v1/tasks/{task['id']}").json() == task


# --- update ---


def test_update_changes_only_the_fields_sent(client: TestClient) -> None:
    task = create_task(client, title="Old", description="Keep me")

    updated = client.patch(f"/v1/tasks/{task['id']}", json={"title": "New"}).json()

    assert updated["title"] == "New"
    assert updated["description"] == "Keep me"
    assert updated["createdAt"] == task["createdAt"]


def test_update_can_clear_description(client: TestClient) -> None:
    task = create_task(client, description="Remove me")

    response = client.patch(f"/v1/tasks/{task['id']}", json={"description": None})

    assert response.json()["description"] is None


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"title": None}, id="null-title"),
        pytest.param({"title": ""}, id="empty-title"),
        pytest.param({"completed": True}, id="unknown-field"),
    ],
)
def test_update_rejects_invalid_body(client: TestClient, body: dict[str, Any]) -> None:
    task = create_task(client, title="Unchanged")

    response = client.patch(f"/v1/tasks/{task['id']}", json=body)

    assert response.status_code == 422
    assert client.get(f"/v1/tasks/{task['id']}").json() == task


# --- delete ---


def test_delete_removes_the_task(client: TestClient) -> None:
    task = create_task(client)

    assert client.delete(f"/v1/tasks/{task['id']}").json() is True
    assert client.get("/v1/tasks").json() == []


# --- complete ---


def test_complete_marks_the_task_done(client: TestClient) -> None:
    task = create_task(client)

    completed = client.post(f"/v1/tasks/{task['id']}/complete").json()

    assert completed["completed"] is True
    assert completed["completedAt"] is not None


def test_complete_is_idempotent(client: TestClient) -> None:
    task = create_task(client)

    first = client.post(f"/v1/tasks/{task['id']}/complete").json()
    second = client.post(f"/v1/tasks/{task['id']}/complete").json()

    assert second == first


# --- not implemented yet ---
# README acceptance criteria the app doesn't meet yet (Stage 2). pytest runs with
# strict xfail, so once one of these starts passing it fails the run as a
# reminder to delete its marker.

stage_2 = pytest.mark.xfail(reason="Stage 2: status codes not implemented yet")


@stage_2
@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        pytest.param("GET", "/v1/tasks/999", None, id="get"),
        pytest.param("PATCH", "/v1/tasks/999", {"title": "x"}, id="update"),
        pytest.param("DELETE", "/v1/tasks/999", None, id="delete"),
        pytest.param("POST", "/v1/tasks/999/complete", None, id="complete"),
    ],
)
def test_missing_task_returns_404(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    assert client.request(method, path, json=body).status_code == 404


@stage_2
def test_create_returns_201(client: TestClient) -> None:
    assert client.post("/v1/tasks", json={"title": "x"}).status_code == 201


@stage_2
def test_delete_returns_204(client: TestClient) -> None:
    task = create_task(client)
    assert client.delete(f"/v1/tasks/{task['id']}").status_code == 204
