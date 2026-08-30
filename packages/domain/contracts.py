from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from .enums import (
    CivilServiceAppointmentRoute,
    CivilServiceCategory,
    CivilServiceEventType,
    EmploymentReviewDecision,
    EpistemicStatus,
    EvidenceStance,
    GovernanceRelationType,
    IdentityStatus,
    InstitutionalBodyType,
    LegalCareerEventType,
    LegalCareerType,
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


class InstitutionalBody(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    body_type: InstitutionalBodyType
    legal_basis: str | None = None
    parent_organization_id: UUID | None = None
    standing: bool | None = None
    source_ids: list[UUID] = Field(min_length=1)


class CommitteeMembershipEpisode(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    institutional_body_id: UUID
    role: str = Field(min_length=1)
    standing_member: bool | None = None
    compensation_text: str | None = None
    claim_ids: list[UUID] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence_required(self) -> CommitteeMembershipEpisode:
        if not self.claim_ids and not self.source_ids:
            raise ValueError("committee membership requires claim_ids or source_ids")
        return self


class OwnershipStake(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    owner_organization_id: UUID | None = None
    owner_person_id: UUID | None = None
    target_organization_id: UUID
    percentage: float | None = Field(default=None, ge=0, le=100)
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = None
    share_class: str | None = None
    direct: bool = True
    as_of: date
    source_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def ownership_semantics(self) -> OwnershipStake:
        if (self.owner_organization_id is None) == (self.owner_person_id is None):
            raise ValueError("ownership stake requires exactly one owner")
        if self.percentage is None and self.amount is None:
            raise ValueError("ownership stake requires percentage or amount")
        if self.amount is not None and not self.currency:
            raise ValueError("ownership amount requires currency")
        return self


class GovernanceSelectionEvent(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    target_organization_id: UUID
    target_person_id: UUID | None = None
    target_office_id: UUID | None = None
    event_date: date
    selection_steps: list[str] = Field(min_length=1)
    nominating_organization_id: UUID | None = None
    recommending_organization_id: UUID | None = None
    approving_organization_id: UUID | None = None
    appointing_authority_organization_id: UUID | None = None
    source_ids: list[UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def selection_target_required(self) -> GovernanceSelectionEvent:
        if self.target_person_id is None and self.target_office_id is None:
            raise ValueError("governance selection requires target_person_id or target_office_id")
        return self


class BoardSeat(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    person_id: UUID
    board_type: str = Field(min_length=1)
    role: str = Field(min_length=1)
    selection_event_id: UUID | None = None
    source_ids: list[UUID] = Field(min_length=1)


class GovernanceRelation(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    source_organization_id: UUID
    target_organization_id: UUID
    relation_type: GovernanceRelationType
    percentage: float | None = Field(default=None, ge=0, le=100)
    as_of: date | None = None
    source_ids: list[UUID] = Field(min_length=1)


class Office(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID
    title: str = Field(min_length=1)


class Appointment(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    office_id: UUID


class CivilServiceCareerEpisode(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    organization_id: UUID
    office_id: UUID | None = None
    category: CivilServiceCategory
    event_type: CivilServiceEventType
    appointment_route: CivilServiceAppointmentRoute = CivilServiceAppointmentRoute.REGULAR
    title: str = Field(min_length=1)
    grade: str | None = None
    event_date: date
    previous_organization_id: UUID | None = None
    previous_office_id: UUID | None = None
    source_ids: list[UUID] = Field(min_length=1)
    claim_ids: list[UUID] = Field(default_factory=list)


class LegalCareerEpisode(TemporalRecord):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    organization_id: UUID
    office_id: UUID | None = None
    career_type: LegalCareerType
    event_type: LegalCareerEventType
    title: str = Field(min_length=1)
    event_date: date
    previous_organization_id: UUID | None = None
    previous_office_id: UUID | None = None
    public_assignment_domain: str | None = None
    source_ids: list[UUID] = Field(min_length=1)
    claim_ids: list[UUID] = Field(default_factory=list)


class EmploymentReviewEvent(Contract):
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID
    former_organization_id: UUID
    destination_organization_id: UUID
    review_date: date
    decision: EmploymentReviewDecision
    decision_text: str = Field(min_length=1)
    former_title: str | None = None
    destination_title: str | None = None
    employment_start_date: date | None = None
    source_ids: list[UUID] = Field(min_length=1)


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
        if (
            self.status in {RoleFitStatus.EVIDENCED, RoleFitStatus.PARTIAL}
            and not self.claim_ids
            and not self.source_ids
        ):
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
