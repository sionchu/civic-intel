from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid5

from packages.connectors.gukgam_witness_packet import (
    OWNER_COPY_LABEL,
    WITNESS_PACKET_SCHEMA,
    ReviewedGukgamWitnessPacket,
)
from packages.domain.contracts import (
    FeederObservation,
    Organization,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    HUMAN_ASSISTED_CAPTURE,
    reviewed_gukgam_plan_policy,
)

GUKGAM_WITNESS_FEEDER = "gukgam_reviewed_witness"
GUKGAM_WITNESS_SEMANTIC_SCOPE = "national_assembly_audit_witness_request_list"
GUKGAM_WITNESS_SOURCE_CONTRACT = "gukgam_reviewed_witness_list_v2"
OWNER_COPY_SOURCE_CLASS = "owner_supplied_reviewed_copy"
# RFC 2606 reserved TLD: a Source.url placeholder that can never be fetched or mistaken
# for an official location. The real, unconfirmed location is not stored anywhere.
OWNER_COPY_PLACEHOLDER_DOMAIN = "owner-supplied-copy.invalid"
OWNER_COPY_RIGHTS_SCOPE = "OWNER_SUPPLIED_COPY_METADATA_ONLY"
_OWNER_POLICY_NAMESPACE = UUID("6d0b6b0e-4e0c-4d0e-9b7b-7a1b7f3f5c21")
CLAIM_SUBJECT_AVAILABLE = "available"
CLAIM_SUBJECT_UNAVAILABLE = "claim_subject_unavailable"
CLAIM_SUBJECT_NOT_CHECKED = "not_checked"


class GukgamWitnessImportError(ValueError):
    """A witness packet lacks exact provenance or review required for persistence."""


@dataclass(frozen=True)
class GukgamWitnessCapture:
    packet: ReviewedGukgamWitnessPacket
    policy: SourcePolicy
    source: Source
    snapshot: SourceSnapshot

    @property
    def scope_key(self) -> str:
        return self.packet.scope_key

    @property
    def packet_hash(self) -> str:
        return self.packet.content_hash

    @property
    def cursor(self) -> str:
        return f"{self.packet.source.artifact_sha256}:{self.packet_hash}"

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
            "packet_schema": WITNESS_PACKET_SCHEMA,
            "review_status": self.packet.review_status,
            "reviewed_packet_hash": self.packet_hash,
            "acquisition_channel": self.packet.source.acquisition_channel,
            "artifact_sha256": self.packet.source.artifact_sha256,
            "list_version": self.packet.source.list_version,
            "witness_row_count": len(self.packet.rows),
        }

    @property
    def checkpoint_metadata(self) -> dict[str, object]:
        return self.run_metadata

    def observations(self, run_id: UUID) -> tuple[FeederObservation, ...]:
        source = self.packet.source
        items: list[FeederObservation] = []
        for row in self.packet.rows:
            normalized: dict[str, object] = {
                "committee_name": source.committee_name,
                "list_title": source.list_title,
                "list_version": source.list_version,
                "list_year": source.list_year,
                "adoption_date": (
                    source.adoption_date.isoformat() if source.adoption_date else None
                ),
                "assumed_year": source.assumed_year.year if source.assumed_year else None,
                "assumed_year_basis": (
                    source.assumed_year.basis if source.assumed_year else None
                ),
                "acquisition_channel": source.acquisition_channel,
                "artifact_format": source.artifact_format,
                "received_via": source.received_via,
                "received_at": source.received_at.isoformat() if source.received_at else None,
                "packet_schema": WITNESS_PACKET_SCHEMA,
            } | row.normalized()
            digest = hashlib.sha256(
                json.dumps(
                    normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode("utf-8")
            ).hexdigest()
            items.append(
                FeederObservation(
                    feeder=GUKGAM_WITNESS_FEEDER,
                    scope_key=self.scope_key,
                    provider_record_key=self.packet.record_key(row),
                    snapshot_id=self.snapshot.id,
                    run_id=run_id,
                    semantic_scope=GUKGAM_WITNESS_SEMANTIC_SCOPE,
                    # Witnesses are never identity candidates: no name hints.
                    identity_hints={},
                    normalized=normalized,
                    content_hash=digest,
                )
            )
        return tuple(items)


def owner_supplied_witness_policy() -> SourcePolicy:
    """Policy for an owner-supplied copy whose official location is unconfirmed."""

    return SourcePolicy(
        id=uuid5(_OWNER_POLICY_NAMESPACE, OWNER_COPY_PLACEHOLDER_DOMAIN),
        domain=OWNER_COPY_PLACEHOLDER_DOMAIN,
        source_class=OWNER_COPY_SOURCE_CLASS,
        collection_mode=SourceCollectionMode.BROWSER,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=datetime(2026, 10, 4, tzinfo=UTC),
        license=None,
        policy_note=(
            "Owner-supplied copy of a committee witness list; official posting location "
            "not yet confirmed. Metadata storage only; every projection row must carry "
            f"the label '{OWNER_COPY_LABEL}'."
        ),
    )


def committee_organization(
    organizations: Iterable[Organization], committee_name: str
) -> Organization | None:
    """The current committee Organization, only if one already exists (never created)."""

    names = (committee_name, f"국회 {committee_name}")
    for organization in organizations:
        if organization.superseded_at is None and organization.name in names:
            return organization
    return None


def claim_subject_status(
    organizations: Iterable[Organization] | None, committee_name: str
) -> str:
    """`claim_subject_unavailable` => observation-only; the lane never creates Organizations."""

    if organizations is None:
        return CLAIM_SUBJECT_NOT_CHECKED
    if committee_organization(organizations, committee_name) is None:
        return CLAIM_SUBJECT_UNAVAILABLE
    return CLAIM_SUBJECT_AVAILABLE


def build_gukgam_witness_capture(
    packet: ReviewedGukgamWitnessPacket,
    *,
    artifact_bytes: bytes,
) -> GukgamWitnessCapture:
    """Bind a reviewed packet to the exact human-captured artifact bytes."""

    if not packet.is_human_reviewed:
        raise GukgamWitnessImportError(
            "witness packet must be HUMAN_REVIEWED before it can be persisted"
        )
    if not packet.rows:
        raise GukgamWitnessImportError("witness packet has no reviewed rows")
    if not artifact_bytes:
        raise GukgamWitnessImportError("witness artifact is empty")
    actual = hashlib.sha256(artifact_bytes).hexdigest()
    if actual != packet.source.artifact_sha256:
        raise GukgamWitnessImportError(
            "witness artifact sha256 does not match the reviewed packet"
        )
    packet_source = packet.source
    filename = packet_source.artifact_filename or packet_source.list_title
    metadata: dict[str, object] = {
        "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
        "acquisition_channel": packet_source.acquisition_channel,
        "artifact_format": packet_source.artifact_format,
        "artifact_filename": packet_source.artifact_filename,
        "list_title": packet_source.list_title,
        "list_version": packet_source.list_version,
        "list_year": packet_source.list_year,
        "adoption_date": (
            packet_source.adoption_date.isoformat() if packet_source.adoption_date else None
        ),
        "rights_mark": packet_source.rights_mark or "NOT_STATED",
        "capture_mode": HUMAN_ASSISTED_CAPTURE,
        "content_hash_semantics": "RAW_ARTIFACT_SHA256",
    }
    if packet_source.is_owner_supplied_copy:
        assert packet_source.received_at is not None
        policy = owner_supplied_witness_policy()
        url = f"https://{OWNER_COPY_PLACEHOLDER_DOMAIN}/gukgam-witness/{actual}"
        publisher = f"{OWNER_COPY_LABEL} — 국회 {packet_source.committee_name}"
        metadata |= {
            "provenance_label": OWNER_COPY_LABEL,
            "official_location": "UNCONFIRMED",
            "received_via": packet_source.received_via,
            "received_at": packet_source.received_at.isoformat(),
            "rights_scope": OWNER_COPY_RIGHTS_SCOPE,
        }
    else:
        assert packet_source.attachment_url and packet_source.page_url
        domain = urlparse(packet_source.attachment_url).hostname or ""
        policy = reviewed_gukgam_plan_policy(domain)
        url = packet_source.attachment_url
        publisher = f"대한민국 국회 {packet_source.committee_name}"
        metadata |= {
            "parent_page_url": packet_source.page_url,
            "rights_scope": EXACT_ATTACHMENT_RIGHTS,
        }
    if packet_source.assumed_year is not None:
        metadata["assumed_year"] = packet_source.assumed_year.year
        metadata["assumed_year_basis"] = packet_source.assumed_year.basis
    source = Source(
        url=url,  # type: ignore[arg-type]
        title=f"{filename} — {packet_source.committee_name}",
        publisher=publisher,
        published_at=None,
        policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=actual,
        metadata=metadata,
        fulltext=None,
    )
    return GukgamWitnessCapture(
        packet=packet, policy=policy, source=source, snapshot=snapshot
    )
