from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse
from uuid import UUID, uuid5

from packages.connectors.gukgam_reviewed_packet import (
    AUTOMATION_GATE,
    PACKET_SCHEMA,
    REVIEW_STATUS,
    GukgamReviewedPacketError,
    ReviewedGukgamPlanPacket,
)
from packages.domain.contracts import (
    FeederObservation,
    Source,
    SourcePolicy,
    SourceSnapshot,
)
from packages.domain.enums import SourceCollectionMode

GUKGAM_REVIEWED_PLAN_FEEDER = "gukgam_reviewed_plan"
GUKGAM_REVIEWED_PLAN_SEMANTIC_SCOPE = "national_assembly_audit_plan_schedule"
GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT = "gukgam_reviewed_plan_attachment_v1"
EXACT_ATTACHMENT_RIGHTS = "EXACT_ATTACHMENT_REVIEWED"
HUMAN_ASSISTED_CAPTURE = "HUMAN_ASSISTED_LOCAL_ARTIFACT"
_POLICY_NAMESPACE = UUID("17bbf4d7-88ef-4d37-81bc-d7801a106f9f")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class GukgamReviewedPlanImportError(ValueError):
    """A reviewed plan packet lacks exact source provenance required for persistence."""


@dataclass(frozen=True)
class ReviewedGukgamArtifactProof:
    attachment_url: str
    attachment_sha256: str
    rights_scope: str = EXACT_ATTACHMENT_RIGHTS
    capture_mode: str = HUMAN_ASSISTED_CAPTURE

    @classmethod
    def from_bytes(
        cls,
        packet: ReviewedGukgamPlanPacket,
        *,
        attachment_url: str,
        artifact_bytes: bytes,
        rights_scope: str = EXACT_ATTACHMENT_RIGHTS,
    ) -> ReviewedGukgamArtifactProof:
        if not artifact_bytes:
            raise GukgamReviewedPlanImportError("reviewed Gukgam artifact is empty")
        proof = cls(
            attachment_url=attachment_url,
            attachment_sha256=hashlib.sha256(artifact_bytes).hexdigest(),
            rights_scope=rights_scope,
        )
        proof.validate(packet)
        return proof

    def validate(self, packet: ReviewedGukgamPlanPacket) -> None:
        if self.rights_scope != EXACT_ATTACHMENT_RIGHTS:
            raise GukgamReviewedPlanImportError(
                "canonical packet import requires exact attachment rights review"
            )
        if self.capture_mode != HUMAN_ASSISTED_CAPTURE:
            raise GukgamReviewedPlanImportError(
                "canonical packet import requires human-assisted local artifact capture"
            )
        if not _SHA256.fullmatch(self.attachment_sha256):
            raise GukgamReviewedPlanImportError(
                "reviewed Gukgam attachment_sha256 is invalid"
            )

        attachment = urlparse(self.attachment_url)
        detail = urlparse(packet.source.detail_url)
        if (
            attachment.scheme != "https"
            or not (attachment.hostname or "").endswith(".na.go.kr")
            or attachment.hostname != detail.hostname
        ):
            raise GukgamReviewedPlanImportError(
                "reviewed Gukgam attachment URL must use the exact official committee host"
            )
        query = parse_qs(attachment.query, keep_blank_values=True)
        if query.get("atchFileId") != [packet.source.atch_file_id]:
            raise GukgamReviewedPlanImportError(
                "reviewed Gukgam attachment URL atchFileId does not match packet"
            )
        if query.get("fileSn") != [str(packet.source.file_sn)]:
            raise GukgamReviewedPlanImportError(
                "reviewed Gukgam attachment URL fileSn does not match packet"
            )
        lowered_keys = {key.casefold() for key in query}
        if {"key", "authkey", "servicekey", "token"} & lowered_keys:
            raise GukgamReviewedPlanImportError(
                "reviewed Gukgam attachment URL must not contain credentials"
            )


@dataclass(frozen=True)
class ReviewedGukgamPlanCapture:
    packet: ReviewedGukgamPlanPacket
    artifact: ReviewedGukgamArtifactProof
    policy: SourcePolicy
    source: Source
    snapshot: SourceSnapshot
    scope_key: str

    @property
    def packet_hash(self) -> str:
        return self.packet.content_hash

    @property
    def cursor(self) -> str:
        return f"{self.artifact.attachment_sha256}:{self.packet_hash}"

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
            "packet_schema": PACKET_SCHEMA,
            "review_status": REVIEW_STATUS,
            "reviewed_packet_hash": self.packet_hash,
            "attachment_sha256": self.artifact.attachment_sha256,
            "rights_scope": self.artifact.rights_scope,
            "capture_mode": self.artifact.capture_mode,
            "schedule_row_count": len(self.packet.schedule),
        }

    @property
    def checkpoint_metadata(self) -> dict[str, object]:
        return self.run_metadata | {
            "ntt_id": self.packet.source.ntt_id,
            "atch_file_id": self.packet.source.atch_file_id,
            "file_sn": self.packet.source.file_sn,
        }

    def observations(self, run_id: UUID) -> tuple[FeederObservation, ...]:
        items: list[FeederObservation] = []
        for row in self.packet.schedule:
            normalized = {
                "committee_name": self.packet.source.committee_name,
                "source_published_date": self.packet.source.published_date.isoformat(),
                "audit_date": row.audit_date.isoformat(),
                "time_text": row.time_text,
                "venue": row.venue,
                "section": row.section,
                "audited_targets": list(row.audited_targets),
                "page_number": row.page_number,
                "packet_schema": PACKET_SCHEMA,
            }
            digest = hashlib.sha256(
                json.dumps(
                    normalized,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            items.append(
                FeederObservation(
                    feeder=GUKGAM_REVIEWED_PLAN_FEEDER,
                    scope_key=self.scope_key,
                    provider_record_key=self.packet.schedule_record_key(row),
                    snapshot_id=self.snapshot.id,
                    run_id=run_id,
                    semantic_scope=GUKGAM_REVIEWED_PLAN_SEMANTIC_SCOPE,
                    identity_hints={},
                    normalized=normalized,
                    content_hash=digest,
                )
            )
        return tuple(items)


def reviewed_gukgam_plan_policy(domain: str) -> SourcePolicy:
    if not domain.endswith(".na.go.kr"):
        raise GukgamReviewedPlanImportError(
            "reviewed Gukgam policy requires an official committee domain"
        )
    return SourcePolicy(
        id=uuid5(_POLICY_NAMESPACE, domain),
        domain=domain,
        source_class="official_reviewed_committee_attachment",
        collection_mode=SourceCollectionMode.BROWSER,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=datetime(2026, 9, 19, tzinfo=UTC),
        license=None,
        policy_note=(
            "Human-assisted exact attachment review only. Repeated automated committee-site "
            "collection remains blocked. Per-attachment rights mark is retained in SourceSnapshot "
            "metadata; this policy authorizes metadata storage only."
        ),
    )


def build_reviewed_gukgam_plan_capture(
    packet: ReviewedGukgamPlanPacket,
    *,
    artifact: ReviewedGukgamArtifactProof,
) -> ReviewedGukgamPlanCapture:
    if packet.source.automation_gate != AUTOMATION_GATE:
        raise GukgamReviewedPlanImportError(
            "reviewed Gukgam packet automation gate changed unexpectedly"
        )
    if not packet.schedule:
        raise GukgamReviewedPlanImportError(
            "canonical packet import requires at least one reviewed schedule row"
        )
    artifact.validate(packet)

    parsed = urlparse(artifact.attachment_url)
    domain = parsed.hostname or ""
    policy = reviewed_gukgam_plan_policy(domain)
    source = Source(
        url=artifact.attachment_url,
        title=f"{packet.source.attachment_filename} — {packet.source.committee_name}",
        publisher=f"대한민국 국회 {packet.source.committee_name}",
        published_at=None,
        policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash=artifact.attachment_sha256,
        metadata={
            "source_contract": GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT,
            "parent_detail_url": packet.source.detail_url,
            "ntt_id": packet.source.ntt_id,
            "atch_file_id": packet.source.atch_file_id,
            "file_sn": packet.source.file_sn,
            "attachment_filename": packet.source.attachment_filename,
            "rights_mark": packet.source.rights_mark,
            "rights_scope": artifact.rights_scope,
            "capture_mode": artifact.capture_mode,
            "content_hash_semantics": "RAW_ATTACHMENT_SHA256",
        },
        fulltext=None,
    )
    return ReviewedGukgamPlanCapture(
        packet=packet,
        artifact=artifact,
        policy=policy,
        source=source,
        snapshot=snapshot,
        scope_key=f"{packet.source.published_date.year}:{packet.source.committee_name}",
    )


def validate_reviewed_gukgam_capture_metadata(
    metadata: Mapping[str, object],
) -> None:
    if metadata.get("source_contract") != GUKGAM_REVIEWED_PLAN_SOURCE_CONTRACT:
        raise GukgamReviewedPlanImportError("reviewed Gukgam source contract is invalid")
    if metadata.get("content_hash_semantics") != "RAW_ATTACHMENT_SHA256":
        raise GukgamReviewedPlanImportError(
            "reviewed Gukgam SourceSnapshot must hash the raw attachment"
        )
    if "reviewed_packet_hash" in metadata:
        raise GukgamReviewedPlanImportError(
            "reviewed packet hash belongs to SourceRun metadata, not SourceSnapshot metadata"
        )
