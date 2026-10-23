"""Unit tests for model behaviour the HTTP tests don't reach yet (pagination)."""

import pytest
from pydantic import ValidationError

from app.models import PagedResult, Task, TaskPage


@pytest.mark.parametrize(
    ("total", "page_size", "expected"),
    [
        pytest.param(0, 20, 0, id="no-results"),
        pytest.param(1, 20, 1, id="one-result"),
        pytest.param(20, 20, 1, id="exactly-one-page"),
        pytest.param(21, 20, 2, id="one-over"),
        pytest.param(45, 20, 3, id="partial-last-page"),
    ],
)
def test_total_pages(total: int, page_size: int, expected: int) -> None:
    page = PagedResult[Task](data=[], total=total, page=1, page_size=page_size)
    assert page.total_pages == expected


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param({"total": -1, "page": 1, "page_size": 20}, id="negative-total"),
        pytest.param({"total": 0, "page": 0, "page_size": 20}, id="page-zero"),
        pytest.param({"total": 0, "page": 1, "page_size": 0}, id="page-size-zero"),
    ],
)
def test_paged_result_rejects_out_of_range_numbers(fields: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        PagedResult[Task](data=[], **fields)


def test_task_page_serializes_camel_case_with_total_pages() -> None:
    page = TaskPage(data=[], total=45, page=1, page_size=20)

    assert page.model_dump(by_alias=True) == {
        "data": [],
        "total": 45,
        "page": 1,
        "pageSize": 20,
        "totalPages": 3,
    }


def test_task_page_keeps_its_name_and_description_in_the_schema() -> None:
    schema = TaskPage.model_json_schema()

    assert schema["title"] == "TaskPage"
    assert schema["description"] == TaskPage.__doc__
