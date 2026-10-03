from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from packages.connectors.gukgam_witness_packet import (
    WITNESS_PACKET_SCHEMA,
    ReviewedGukgamWitnessPacket,
)
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    HUMAN_ASSISTED_CAPTURE,
    reviewed_gukgam_plan_policy,
)

GUKGAM_WITNESS_FEEDER = "gukgam_reviewed_witness"
GUKGAM_WITNESS_SEMANTIC_SCOPE = "national_assembly_audit_witness_request_list"
GUKGAM_WITNESS_SOURCE_CONTRACT = "gukgam_reviewed_witness_list_v1"


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
        return f"{self.packet.source.attachment_sha256}:{self.packet_hash}"

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
            "packet_schema": WITNESS_PACKET_SCHEMA,
            "review_status": self.packet.review_status,
            "reviewed_packet_hash": self.packet_hash,
            "attachment_sha256": self.packet.source.attachment_sha256,
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
                "adoption_date": source.adoption_date.isoformat(),
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
    if actual != packet.source.attachment_sha256:
        raise GukgamWitnessImportError(
            "witness artifact sha256 does not match the reviewed packet"
        )
    domain = urlparse(packet.source.attachment_url).hostname or ""
    policy = reviewed_gukgam_plan_policy(domain)
    source = Source(
        url=packet.source.attachment_url,
        title=f"{packet.source.attachment_filename} — {packet.source.committee_name}",
        publisher=f"대한민국 국회 {packet.source.committee_name}",
        published_at=None,
        policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=actual,
        metadata={
            "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
            "parent_page_url": packet.source.page_url,
            "attachment_filename": packet.source.attachment_filename,
            "attachment_type": packet.source.attachment_type,
            "list_title": packet.source.list_title,
            "list_version": packet.source.list_version,
            "adoption_date": packet.source.adoption_date.isoformat(),
            "rights_mark": packet.source.rights_mark or "NOT_STATED",
            "rights_scope": EXACT_ATTACHMENT_RIGHTS,
            "capture_mode": HUMAN_ASSISTED_CAPTURE,
            "content_hash_semantics": "RAW_ATTACHMENT_SHA256",
        },
        fulltext=None,
    )
    return GukgamWitnessCapture(
        packet=packet, policy=policy, source=source, snapshot=snapshot
    )
