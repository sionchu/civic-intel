from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    RelationshipStrength,
    SourceCollectionMode,
)


def now_utc() -> datetime:
    return datetime.now(UTC)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class TemporalRecord(Contract):
    valid_from: datetime = Field(default_factory=now_utc)
    valid_to: datetime | None = None
    recorded_at: datetime = Field(default_factory=now_utc)
    superseded_at: datetime | None = None

    @model_validator(mode="after")
    def ordered_intervals(self) -> TemporalRecord:
        if self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to precedes valid_from")
        if self.superseded_at and self.superseded_at < self.recorded_at:
            raise ValueError("superseded_at precedes recorded_at")
        return self


class Person(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    canonical_name: str = Field(min_length=1)
    birth_date: date | None = None
    identity_status: IdentityStatus = IdentityStatus.UNRESOLVED


class PersonAlias(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    name: str = Field(min_length=1)


class Organization(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(min_length=1)


class Office(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    title: str = Field(min_length=1)


class Appointment(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    office_id: UUID


class SourcePolicy(Contract):
    id: UUID = Field(default_factory=uuid4)
    domain: str = Field(min_length=1)
    source_class: str = Field(min_length=1)
    collection_mode: SourceCollectionMode
    can_fetch: bool
    can_store_metadata: bool
    can_store_fulltext: bool
    can_send_to_ai: bool
    can_show_excerpt: bool
    can_commercialize: bool
    robots_checked_at: datetime | None = None
    terms_checked_at: datetime | None = None
    license: str | None = None
    rate_limit: str | None = None
    policy_note: str | None = None


class Source(Contract):
    id: UUID = Field(default_factory=uuid4)
    url: HttpUrl
    title: str
    publisher: str
    published_at: datetime | None = None
    policy_id: UUID
    origin_cluster_id: UUID | None = None


class SourceSnapshot(Contract):
    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    fetched_at: datetime = Field(default_factory=now_utc)
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    fulltext: str | None = None


class SourceOriginCluster(Contract):
    id: UUID = Field(default_factory=uuid4)
    canonical_source_id: UUID
    member_source_ids: list[UUID] = Field(min_length=1)
    reason: str


class Claim(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    proposition: str = Field(min_length=1)
    epistemic_status: EpistemicStatus
    published: bool = False


class ClaimEvidence(Contract):
    id: UUID = Field(default_factory=uuid4)
    claim_id: UUID
    source_id: UUID
    snapshot_id: UUID | None = None
    stance: EvidenceStance
    excerpt: str | None = None


class AssetItem(Contract):
    id: UUID = Field(default_factory=uuid4)
    description: str
    value: float | None = None
    currency: str | None = None
    claim_id: UUID | None = None


class AssetDisclosure(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    source_id: UUID
    items: list[AssetItem] = Field(default_factory=list)


class Event(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    name: str


class EventDocument(Contract):
    id: UUID = Field(default_factory=uuid4)
    event_id: UUID
    source_id: UUID


class DecisionEpisode(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    description: str
    source_ids: list[UUID] = Field(min_length=1)


class Relationship(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    related_person_id: UUID | None = None
    related_organization_id: UUID | None = None
    relationship_type: str
    strength: RelationshipStrength
    evidence_ids: list[UUID] = Field(default_factory=list)


class Hypothesis(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    statement: str
    ordinary_explanation: str = Field(min_length=1)
    falsifier: str = Field(min_length=1)
    published: bool = False


class HypothesisEvidence(Contract):
    id: UUID = Field(default_factory=uuid4)
    hypothesis_id: UUID
    claim_evidence_id: UUID
    stance: EvidenceStance


class ProfileSnapshot(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    claim_ids: list[UUID] = Field(default_factory=list)
    relationship_ids: list[UUID] = Field(default_factory=list)
    asset_disclosure_ids: list[UUID] = Field(default_factory=list)
