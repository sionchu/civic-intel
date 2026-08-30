from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .enums import (
    EpistemicStatus,
    EvidenceStance,
    IdentityStatus,
    PublicationStatus,
    RelationshipEvidenceType,
    RelationshipStrength,
    RoleFitStatus,
    SourceCollectionMode,
    TalentPoolBucket,
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


class AppointmentTarget(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1)
    institution: str = Field(min_length=1)
    appointment_route: str = Field(min_length=1)
    hearing_required: bool | None = None
    role_fit_dimensions: list[str] = Field(min_length=1)
    source_ids: list[UUID] = Field(min_length=1)
    note: str | None = None

    @model_validator(mode="after")
    def unique_dimensions(self) -> AppointmentTarget:
        if len(set(self.role_fit_dimensions)) != len(self.role_fit_dimensions):
            raise ValueError("role_fit_dimensions must be unique")
        return self


class RoleFitEvidence(Contract):
    dimension: str = Field(min_length=1)
    status: RoleFitStatus
    claim_ids: list[UUID] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    note: str | None = None

    @model_validator(mode="after")
    def evidence_semantics(self) -> RoleFitEvidence:
        if self.status in {RoleFitStatus.EVIDENCED, RoleFitStatus.PARTIAL}:
            if not self.claim_ids and not self.source_ids:
                raise ValueError("evidenced role fit requires claim_ids or source_ids")
        if self.status in {RoleFitStatus.UNKNOWN, RoleFitStatus.GAP} and not self.note:
            raise ValueError("UNKNOWN/GAP role fit requires a note")
        return self


class TalentPoolEntry(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    appointment_target_id: UUID
    bucket: TalentPoolBucket
    inclusion_reason: str = Field(min_length=1)
    role_fit: list[RoleFitEvidence] = Field(min_length=1)
    actual_consideration_claim_id: UUID | None = None

    @model_validator(mode="after")
    def explainable_inclusion(self) -> TalentPoolEntry:
        dimensions = [item.dimension for item in self.role_fit]
        if len(set(dimensions)) != len(dimensions):
            raise ValueError("role_fit dimensions must be unique within a talent-pool entry")
        if not any(
            item.status in {RoleFitStatus.EVIDENCED, RoleFitStatus.PARTIAL}
            for item in self.role_fit
        ):
            raise ValueError("talent-pool inclusion requires at least one evidenced dimension")
        return self


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
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object_text: str = Field(min_length=1)
    qualifiers: dict[str, str] = Field(default_factory=dict)
    epistemic_status: EpistemicStatus
    publication_status: PublicationStatus = PublicationStatus.DRAFT
    asserted_as_true: bool = False
    resolution_note: str | None = None

    @model_validator(mode="after")
    def publication_semantics(self) -> Claim:
        if self.epistemic_status == EpistemicStatus.FACT and not self.asserted_as_true:
            raise ValueError("FACT must be explicitly asserted_as_true")
        if self.epistemic_status == EpistemicStatus.UNKNOWN:
            if self.asserted_as_true:
                raise ValueError("UNKNOWN cannot be asserted as true")
            if not self.resolution_note:
                raise ValueError("UNKNOWN requires a resolution_note")
        return self


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
    action: str = Field(min_length=1)
    target: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    source_ids: list[UUID] = Field(min_length=1)
    independent_origin_ids: list[UUID] = Field(min_length=1)


class RelationshipEvidenceRef(Contract):
    claim_evidence_id: UUID
    evidence_type: RelationshipEvidenceType


class Relationship(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    related_person_id: UUID | None = None
    related_organization_id: UUID | None = None
    relationship_type: str
    strength: RelationshipStrength
    evidence: list[RelationshipEvidenceRef] = Field(default_factory=list)


class HypothesisAlternative(Contract):
    label: str = Field(pattern=r"^H[012]$")
    statement: str = Field(min_length=1)
    evidence_ids: list[UUID] = Field(default_factory=list)


class Hypothesis(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    statement: str
    ordinary_explanation: str = Field(min_length=1)
    falsifier: str = Field(min_length=1)
    alternatives: list[HypothesisAlternative] = Field(min_length=3, max_length=3)
    publication_status: PublicationStatus = PublicationStatus.DRAFT

    @model_validator(mode="after")
    def complete_matrix(self) -> Hypothesis:
        if {item.label for item in self.alternatives} != {"H0", "H1", "H2"}:
            raise ValueError("hypothesis matrix must contain H0, H1, and H2")
        return self


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
