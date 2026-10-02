from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from packages.connectors.gukgam_witness_packet import (
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
