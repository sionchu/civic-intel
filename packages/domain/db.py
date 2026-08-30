from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TemporalMixin:
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PersonRow(TemporalMixin, Base):
    __tablename__ = "people"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    canonical_name: Mapped[str] = mapped_column(String(300), index=True)
    birth_date: Mapped[date | None] = mapped_column(Date)
    identity_status: Mapped[str] = mapped_column(String(32), index=True)


class PersonAliasRow(TemporalMixin, Base):
    __tablename__ = "person_aliases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    name: Mapped[str] = mapped_column(String(300), index=True)


class OrganizationRow(TemporalMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(300), index=True)


class OfficeRow(TemporalMixin, Base):
    __tablename__ = "offices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String(300))


class AppointmentRow(TemporalMixin, Base):
    __tablename__ = "appointments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"))
    office_id: Mapped[str] = mapped_column(ForeignKey("offices.id"))


class SourcePolicyRow(Base):
    __tablename__ = "source_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    domain: Mapped[str] = mapped_column(String(255), unique=True)
    source_class: Mapped[str] = mapped_column(String(80))
    collection_mode: Mapped[str] = mapped_column(String(32))
    can_fetch: Mapped[bool] = mapped_column(Boolean)
    can_store_metadata: Mapped[bool] = mapped_column(Boolean)
    can_store_fulltext: Mapped[bool] = mapped_column(Boolean)
    can_send_to_ai: Mapped[bool] = mapped_column(Boolean)
    can_show_excerpt: Mapped[bool] = mapped_column(Boolean)
    can_commercialize: Mapped[bool] = mapped_column(Boolean)
    robots_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    license: Mapped[str | None] = mapped_column(String(255))
    rate_limit: Mapped[str | None] = mapped_column(String(100))
    policy_note: Mapped[str | None] = mapped_column(Text)


class SourceRow(Base):
    __tablename__ = "sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(String(300))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    policy_id: Mapped[str] = mapped_column(ForeignKey("source_policies.id"))
    origin_cluster_id: Mapped[str | None] = mapped_column(String(36), index=True)


class SourceSnapshotRow(Base):
    __tablename__ = "source_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    fulltext: Mapped[str | None] = mapped_column(Text)


class SourceRunRow(Base):
    __tablename__ = "source_runs"
    __table_args__ = (Index("ix_source_runs_feeder_scope", "feeder", "scope_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feeder: Mapped[str] = mapped_column(String(100), index=True)
    scope_key: Mapped[str] = mapped_column(String(300))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), index=True)
    checkpoint_before: Mapped[str | None] = mapped_column(Text)
    checkpoint_after: Mapped[str | None] = mapped_column(Text)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    observations_created: Mapped[int] = mapped_column(Integer, default=0)
    observations_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(120))
    error_summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON)


class SourceCheckpointRow(Base):
    __tablename__ = "source_checkpoints"
    __table_args__ = (
        UniqueConstraint("feeder", "scope_key", name="uq_source_checkpoints_feeder_scope"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feeder: Mapped[str] = mapped_column(String(100))
    scope_key: Mapped[str] = mapped_column(String(300))
    cursor: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_runs.id"), index=True
    )


class FeederObservationRow(Base):
    __tablename__ = "feeder_observations"
    __table_args__ = (
        UniqueConstraint(
            "feeder",
            "scope_key",
            "provider_record_key",
            "content_hash",
            name="uq_feeder_observations_version",
        ),
        Index(
            "ix_feeder_observations_feeder_provider",
            "feeder",
            "provider_record_key",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    feeder: Mapped[str] = mapped_column(String(100))
    scope_key: Mapped[str] = mapped_column(String(300))
    provider_record_key: Mapped[str] = mapped_column(String(500))
    snapshot_id: Mapped[str] = mapped_column(ForeignKey("source_snapshots.id"), index=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("source_runs.id"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider_observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    semantic_scope: Mapped[str] = mapped_column(String(120), index=True)
    identity_hints_json: Mapped[dict] = mapped_column(JSON)
    normalized_json: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)


class IdentityReviewItemRow(Base):
    __tablename__ = "identity_review_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("feeder_observations.id"), index=True
    )
    candidate_person_id: Mapped[str | None] = mapped_column(
        ForeignKey("people.id"), index=True
    )
    reason_code: Mapped[str] = mapped_column(String(100), index=True)
    details_json: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)


class PersonObservationLinkRow(Base):
    __tablename__ = "person_observation_links"
    __table_args__ = (
        UniqueConstraint(
            "person_id", "observation_id", name="uq_person_observation_links_pair"
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    observation_id: Mapped[str] = mapped_column(
        ForeignKey("feeder_observations.id"), index=True
    )
    action: Mapped[str] = mapped_column(String(40), index=True)
    decision_class: Mapped[str] = mapped_column(String(80), index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("identity_review_items.id"), index=True
    )


class SourceOriginClusterRow(Base):
    __tablename__ = "source_origin_clusters"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    canonical_source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))
    member_source_ids: Mapped[list] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)


class ClaimRow(TemporalMixin, Base):
    __tablename__ = "claims"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id"), index=True)
    proposition: Mapped[str] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(Text)
    predicate: Mapped[str] = mapped_column(String(120), index=True)
    object_text: Mapped[str] = mapped_column(Text)
    qualifiers: Mapped[dict] = mapped_column(JSON)
    epistemic_status: Mapped[str] = mapped_column(String(32), index=True)
    publication_status: Mapped[str] = mapped_column(String(32), index=True)
    asserted_as_true: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_note: Mapped[str | None] = mapped_column(Text)


class ClaimEvidenceRow(Base):
    __tablename__ = "claim_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(ForeignKey("claims.id"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"), index=True)
    snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("source_snapshots.id"))
    feeder_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("feeder_observations.id"), index=True
    )
    stance: Mapped[str] = mapped_column(String(16))
    excerpt: Mapped[str | None] = mapped_column(Text)


class JsonTemporalRow(TemporalMixin):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)


class AssetDisclosureRow(JsonTemporalRow, Base):
    __tablename__ = "asset_disclosures"


class AssetItemRow(Base):
    __tablename__ = "asset_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    disclosure_id: Mapped[str] = mapped_column(ForeignKey("asset_disclosures.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(12))
    claim_id: Mapped[str | None] = mapped_column(ForeignKey("claims.id"))


class EventRow(JsonTemporalRow, Base):
    __tablename__ = "events"


class DecisionEpisodeRow(JsonTemporalRow, Base):
    __tablename__ = "decision_episodes"


class RelationshipRow(JsonTemporalRow, Base):
    __tablename__ = "relationships"


class HypothesisRow(JsonTemporalRow, Base):
    __tablename__ = "hypotheses"


class ProfileSnapshotRow(JsonTemporalRow, Base):
    __tablename__ = "profile_snapshots"


class EventDocumentRow(Base):
    __tablename__ = "event_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id"))


class HypothesisEvidenceRow(Base):
    __tablename__ = "hypothesis_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    hypothesis_id: Mapped[str] = mapped_column(ForeignKey("hypotheses.id"))
    claim_evidence_id: Mapped[str] = mapped_column(ForeignKey("claim_evidence.id"))
    stance: Mapped[str] = mapped_column(String(16))
