from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

from packages.connectors.gukgam_witness_packet import (
    DRAFT,
    HUMAN_REVIEWED,
    WITNESS_PACKET_SCHEMA,
    GukgamWitnessPacket,
    GukgamWitnessPacketError,
    canonical_hash,
    parse_gukgam_witness_packet,
)
from packages.domain.contracts import FeederObservation, Source, SourcePolicy, SourceSnapshot
from packages.verification.gukgam_reviewed_plan_import import (
    ReviewedGukgamArtifactProof,
    reviewed_gukgam_plan_policy,
)

GUKGAM_WITNESS_FEEDER = "gukgam_reviewed_witness"
GUKGAM_WITNESS_SCOPE = "national_assembly_audit_source_listed_witness"
GUKGAM_WITNESS_SOURCE_CONTRACT = "gukgam_witness_attachment_v1"
_DRAFT_EDIT_FIELDS = frozenset({
    "source_section", "printed_name", "printed_institution_group", "printed_role",
    "printed_affiliation_role", "printed_audited_target", "requested_datetime_text",
    "decision_date_text",
})


def _draft_preparation_packet(
    packet: GukgamWitnessPacket, artifact: ReviewedGukgamArtifactProof,
) -> GukgamWitnessPacket:
    policy = reviewed_gukgam_plan_policy(urlparse(packet.attachment_url).hostname or "")
    if not policy.can_store_metadata or packet.source.rights_mark != (
        "KOGL_TYPE_1_VISIBLE_ON_EXACT_PARENT_POST"
    ):
        raise GukgamWitnessPacketError("witness draft preparation lacks its metadata rights gate")
    packet = parse_gukgam_witness_packet(packet.normalized())
    if packet.review_status != DRAFT:
        raise GukgamWitnessPacketError("draft preparation requires an unreviewed packet")
    artifact.validate(packet)
    if (
        artifact.attachment_sha256 != packet.attachment_sha256
        or artifact.attachment_url != packet.attachment_url
    ):
        raise GukgamWitnessPacketError("witness draft artifact differs from its packet")
    return packet


def build_gukgam_witness_draft_edits(
    packet: GukgamWitnessPacket, *, artifact: ReviewedGukgamArtifactProof,
) -> dict[str, object]:
    """Local operator template; exporting literal fields is never review attestation."""
    packet = _draft_preparation_packet(packet, artifact)
    return {
        "packet_hash": packet.content_hash, "attachment_sha256": packet.attachment_sha256,
        "rows": [
            {"record_key": row.record_key, "expected_row_hash": canonical_hash(row.model_dump()),
             "fields": {key: value for key, value in row.model_dump().items()
                        if key in _DRAFT_EDIT_FIELDS}}
            for row in packet.rows
        ],
    }


def prepare_gukgam_witness_draft(
    packet: GukgamWitnessPacket, edits: Mapping[str, Any],
    *, artifact: ReviewedGukgamArtifactProof,
) -> GukgamWitnessPacket:
    """Select/correct supplied literal fields; keep source provenance and DRAFT authority."""
    packet = _draft_preparation_packet(packet, artifact)
    if not isinstance(edits, Mapping) or set(edits) != {
        "packet_hash", "attachment_sha256", "rows",
    }:
        raise GukgamWitnessPacketError("witness draft edits contain unsupported fields")
    if (
        edits["packet_hash"] != packet.content_hash
        or edits["attachment_sha256"] != packet.attachment_sha256
    ):
        raise GukgamWitnessPacketError("witness draft edits differ from the pinned input")
    entries = edits["rows"]
    if not isinstance(entries, list) or not entries:
        raise GukgamWitnessPacketError("witness draft edits require an explicit nonempty selection")
    originals = {row.record_key: row for row in packet.rows}
    selected: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "record_key", "expected_row_hash", "fields",
        }:
            raise GukgamWitnessPacketError("witness draft row edits contain unsupported fields")
        key, fields = entry["record_key"], entry["fields"]
        if not isinstance(key, str) or key not in originals or key in selected:
            raise GukgamWitnessPacketError("witness draft selection is unknown or duplicated")
        original = originals[key].model_dump()
        if entry["expected_row_hash"] != canonical_hash(original):
            raise GukgamWitnessPacketError("witness draft row differs from its pinned input")
        if not isinstance(fields, Mapping) or set(fields) - _DRAFT_EDIT_FIELDS:
            raise GukgamWitnessPacketError("witness draft edits require permitted literal fields")
        selected[key] = original | dict(fields)
    normalized = packet.normalized() | {
        "review_status": DRAFT, "selection": "EXPLICIT_REVIEW_SUBSET",
        "rows": [selected[row.record_key] for row in packet.rows if row.record_key in selected],
    }
    return parse_gukgam_witness_packet(normalized)


@dataclass(frozen=True)
class ReviewedGukgamWitnessCapture:
    packet: GukgamWitnessPacket
    artifact: ReviewedGukgamArtifactProof
    policy: SourcePolicy
    source: Source
    snapshot: SourceSnapshot

    @property
    def scope_key(self) -> str:
        # One checkpoint per attachment series; two PDFs never overwrite each other's rows.
        return (
            f"{self.packet.source.published_date.year}:{self.packet.source.committee_name}:"
            f"{self.packet.source_key}"
        )

    @property
    def cursor(self) -> str:
        return f"{self.artifact.attachment_sha256}:{self.packet.content_hash}"

    def normalized_rows(self) -> list[dict[str, object]]:
        return [
            {
                "packet_schema": WITNESS_PACKET_SCHEMA,
                "committee_name": self.packet.source.committee_name,
                "source_published_date": self.packet.source.published_date.isoformat(),
                # Version the observation hash as well as SourceSnapshot. Identical public
                # fields in a byte-changed artifact must retain that artifact's provenance.
                "attachment_sha256": self.artifact.attachment_sha256,
                **row.model_dump(),
            }
            for row in self.packet.rows
        ]

    @property
    def run_metadata(self) -> dict[str, object]:
        return {
            "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
            "packet_schema": WITNESS_PACKET_SCHEMA,
            "review_status": HUMAN_REVIEWED,
            "reviewed_packet_hash": self.packet.content_hash,
            "attachment_sha256": self.artifact.attachment_sha256,
            "selection": self.packet.selection,
            "witness_row_count": len(self.packet.rows),
            "row_manifest": [
                {"record_key": row["record_key"], "content_hash": canonical_hash(row)}
                for row in self.normalized_rows()
            ],
        }

    def observations(self, run_id: UUID) -> list[FeederObservation]:
        return [
            FeederObservation(
                feeder=GUKGAM_WITNESS_FEEDER, scope_key=self.scope_key,
                provider_record_key=str(row["record_key"]), snapshot_id=self.snapshot.id,
                run_id=run_id, semantic_scope=GUKGAM_WITNESS_SCOPE,
                identity_hints={}, normalized=row, content_hash=canonical_hash(row),
            )
            for row in self.normalized_rows()
        ]


def verify_witness_artifact(packet: GukgamWitnessPacket, artifact_bytes: bytes):
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet, attachment_url=packet.attachment_url, artifact_bytes=artifact_bytes,
    )
    if proof.attachment_sha256 != packet.attachment_sha256:
        raise GukgamWitnessPacketError("witness attachment bytes differ from the pinned hash")
    return proof


def build_reviewed_gukgam_witness_capture(
    packet: GukgamWitnessPacket, *, artifact: ReviewedGukgamArtifactProof,
) -> ReviewedGukgamWitnessCapture:
    # Revalidate at the write boundary, including objects constructed outside the parser.
    packet = parse_gukgam_witness_packet(packet.normalized())
    if packet.review_status != HUMAN_REVIEWED:
        raise GukgamWitnessPacketError("witness source fields require actual human review")
    artifact.validate(packet)
    if (
        artifact.attachment_sha256 != packet.attachment_sha256
        or artifact.attachment_url != packet.attachment_url
    ):
        raise GukgamWitnessPacketError("witness artifact proof differs from the packet")
    policy = reviewed_gukgam_plan_policy(urlparse(artifact.attachment_url).hostname or "")
    source = Source(
        url=artifact.attachment_url,
        title=f"{packet.source.attachment_filename} — {packet.source.committee_name}",
        publisher=f"대한민국 국회 {packet.source.committee_name}", policy_id=policy.id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id, content_hash=artifact.attachment_sha256, fulltext=None,
        metadata={
            "source_contract": GUKGAM_WITNESS_SOURCE_CONTRACT,
            "content_hash_semantics": "RAW_ATTACHMENT_SHA256",
            "source": packet.source.normalized(), "page_count": packet.page_count,
            "rights_scope": artifact.rights_scope, "capture_mode": artifact.capture_mode,
        },
    )
    return ReviewedGukgamWitnessCapture(packet, artifact, policy, source, snapshot)
