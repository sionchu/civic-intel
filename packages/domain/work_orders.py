"""Transient, reference-only preparation contract; not a task executor or data authority."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

RecipeId = Literal[
    "collection_check",
    "collection_failure",
    "person_review",
    "identity_link",
    "product_fix",
    "result_check",
]
RecordKind = Literal[
    "observations", "people", "organizations", "claims", "evidence", "runs", "operations"
]


class WorkReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: RecordKind
    id: UUID
    version: str = Field(pattern=r"^[0-9a-f]{64}$")


class WorkOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: UUID
    recipe_id: RecipeId
    references: tuple[WorkReference, ...] = Field(default=(), max_length=25)
    operator_note: str = Field(default="", max_length=1500)
    code_area: Literal["admin", "api", "graph"] = "admin"

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        keys = [(item.kind, item.id) for item in self.references]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate references are not permitted")
        kinds = {item.kind for item in self.references}
        if self.recipe_id in {"collection_check", "collection_failure"}:
            if len(keys) != 1 or kinds != {"runs"}:
                raise ValueError("Select exactly one source run")
        elif self.recipe_id == "person_review":
            if not keys or kinds != {"observations"}:
                raise ValueError("Select 1–25 observations")
        elif self.recipe_id == "identity_link":
            if kinds != {"observations", "people", "evidence"}:
                raise ValueError("Select observation, candidate Person and Evidence")
            if (
                sum(item.kind == "observations" for item in self.references) != 1
                or sum(item.kind == "people" for item in self.references) != 1
            ):
                raise ValueError("Use one observation and one candidate Person")
        elif self.recipe_id == "product_fix":
            if len(self.operator_note.strip()) < 10:
                raise ValueError("Describe the issue and reproduction steps")
        elif not keys and len(self.operator_note.strip()) < 10:
            raise ValueError("Select a result or describe the exact code/verification scope")
        return self
