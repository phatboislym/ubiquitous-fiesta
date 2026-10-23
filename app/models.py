import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator
from pydantic.alias_generators import to_camel

TITLE_MAX_LENGTH = 256
DESCRIPTION_MAX_LENGTH = 2048


class CamelModel(BaseModel):
    """Base for every API model: snake_case in Python, camelCase in JSON."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Task(CamelModel):
    """A task as stored and returned by the API. Timestamps are set by the server."""

    id: int
    title: str
    description: str | None = None
    completed: bool = False
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class TaskCreate(CamelModel):
    """POST body: only title is required. The server sets id, status and timestamps."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    due_date: datetime | None = None


class TaskUpdate(CamelModel):
    """PATCH body: every field is optional, and only the fields sent are applied."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    due_date: datetime | None = None

    @field_validator("title")
    @classmethod
    def title_cannot_be_null(cls, value: str | None) -> str | None:
        # Omitting title is fine (it's left alone), but sending "title": null
        # would blank a required field, so reject it. description and due_date
        # can be set to null to clear them.
        if value is None:
            raise ValueError("title cannot be null")
        return value


class PagedResult[T](CamelModel):
    """One page of a list response, with the totals a client needs to page through."""

    data: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)

    @computed_field  # type: ignore[prop-decorator]  # documented pydantic workaround
    @property
    def total_pages(self) -> int:
        # 0 when there are no results
        return math.ceil(self.total / self.page_size)


# A named subclass, because PagedResult[Task] would lose the docstring and get
# the generated schema name "PagedResult_Task_".
class TaskPage(PagedResult[Task]):
    """One page of tasks from a paginated list endpoint."""
