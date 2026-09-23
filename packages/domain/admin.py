"""Explicit local operator commands. Publication and identity gates remain canonical."""

from __future__ import annotations

from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PERSON_ROLE_PREDICATE = "ALIO_REVIEWED_PERSON_ROLE"
CORRECTION_PREDICATE = "OPERATOR_REVIEWED_CORRECTION"


class AdminAction(StrEnum):
    HOLD = "HOLD"
    EXCLUDE = "EXCLUDE"
    REOPEN = "REOPEN"
    REGISTER_PERSON = "REGISTER_PERSON"
    LINK_PERSON = "LINK_PERSON"
    SUBMIT_REVIEW = "SUBMIT_REVIEW"
    PUBLISH = "PUBLISH"
    WITHDRAW = "WITHDRAW"
    CORRECT_CLAIM = "CORRECT_CLAIM"
    RENAME_PERSON = "RENAME_PERSON"
    DEACTIVATE_PERSON = "DEACTIVATE_PERSON"
    MERGE_PERSON = "MERGE_PERSON"


class AdminCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    request_id: UUID
    action: AdminAction
    record_ids: tuple[UUID, ...] = Field(min_length=1, max_length=25)
    reason: str = Field(min_length=10, max_length=1500)
    target_person_id: UUID | None = None
    evidence_ids: tuple[UUID, ...] = Field(default=(), max_length=12)
    value: str | None = Field(default=None, min_length=1, max_length=1500)
    identity_basis: str | None = None
    human_verified: bool = False

    @model_validator(mode="after")
    def validate_command_shape(self) -> Self:
        if len(set(self.record_ids)) != len(self.record_ids):
            raise ValueError("Duplicate selected records are not permitted")
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate Evidence references are not permitted")
        if len(self.reason.strip()) < 10:
            raise ValueError("A substantive reason is required")
        single = {
            AdminAction.LINK_PERSON,
            AdminAction.CORRECT_CLAIM,
            AdminAction.RENAME_PERSON,
            AdminAction.DEACTIVATE_PERSON,
            AdminAction.MERGE_PERSON,
        }
        if self.action in single and len(self.record_ids) != 1:
            raise ValueError("This operation accepts one selected source record")
        identity = {AdminAction.REGISTER_PERSON, AdminAction.LINK_PERSON, AdminAction.MERGE_PERSON}
        if self.action in identity and not self.human_verified:
            raise ValueError("Identity operations require explicit human review")
        if self.action in {AdminAction.LINK_PERSON, AdminAction.MERGE_PERSON}:
            if self.target_person_id is None or not self.evidence_ids:
                raise ValueError("Link/merge requires a surviving Person and bridge Evidence")
            if self.identity_basis not in {
                "OFFICIAL_CAREER_CONTINUITY",
                "OFFICIAL_BIOGRAPHY_CONTINUITY",
            }:
                raise ValueError("Choose the reviewed official continuity evidence basis")
        elif self.target_person_id is not None or self.identity_basis is not None:
            raise ValueError("Unexpected target identity or bridge basis")
        if self.action in {AdminAction.CORRECT_CLAIM, AdminAction.RENAME_PERSON}:
            if not self.value or not self.value.strip() or not self.evidence_ids:
                raise ValueError("A corrected value and Evidence references are required")
            if self.action == AdminAction.RENAME_PERSON and len(self.value.strip()) > 100:
                raise ValueError("A Person name is at most 100 characters")
        elif self.value is not None:
            raise ValueError("Unexpected edited value")
        if self.evidence_ids and self.action not in {
            AdminAction.LINK_PERSON,
            AdminAction.MERGE_PERSON,
            AdminAction.CORRECT_CLAIM,
            AdminAction.RENAME_PERSON,
        }:
            raise ValueError("This action does not accept extra Evidence")
        return self


class AdminCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: AdminCommand
    preview_token: str = Field(min_length=50, max_length=1000)
    confirmed: bool
