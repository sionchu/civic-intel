"""One local, reviewed witness attachment; acquisition only, never a crawler."""

from __future__ import annotations

import argparse
import json
from collections import Counter

from sqlalchemy.exc import SQLAlchemyError

from packages.application.context import Application
from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacket,
    GukgamWitnessPacketError,
    parse_gukgam_witness_packet,
    parse_gukgam_witness_research,
)
from packages.domain.enums import SourceRunStatus
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    ReviewedGukgamWitnessCapture,
    build_reviewed_gukgam_witness_capture,
    verify_witness_artifact,
)


def inspection(packets: tuple[GukgamWitnessPacket, ...]) -> dict[str, object]:
    counts = Counter(row.category for packet in packets for row in packet.rows)
    return {
        "status": "READ_ONLY_REVIEW_PREPARATION",
        "feeder": GUKGAM_WITNESS_FEEDER,
        "source_documents": len(packets), "row_count": sum(counts.values()),
        "category_counts": dict(sorted(counts.items())),
        "sources": [
            {"committee_name": packet.source.committee_name, "source_key": packet.source_key,
             "attachment_sha256": packet.attachment_sha256, "packet_hash": packet.content_hash,
             "review_status": packet.review_status, "selection": packet.selection,
             "row_count": len(packet.rows)}
            for packet in packets
        ],
        "person_materialization": False, "organization_materialization": False,
        "claim_publication": False, "actual_attendance_verified": False,
        "unique_person_count": None, "latest_amendment_completeness": "NOT_ESTABLISHED",
    }


def load_packet(args: argparse.Namespace) -> GukgamWitnessPacket:
    return parse_gukgam_witness_packet(json.loads(args.packet.read_text(encoding="utf-8")))


def inspect_inputs(args: argparse.Namespace) -> dict[str, object]:
    if args.research:
        packets = parse_gukgam_witness_research(
            json.loads(args.research.read_text(encoding="utf-8"))
        )
        return inspection(packets) | {"artifact_bytes_verified": False}
    packet = load_packet(args)
    verify_witness_artifact(packet, args.artifact.read_bytes())
    return inspection((packet,)) | {"artifact_bytes_verified": True}


def load_capture(args: argparse.Namespace) -> ReviewedGukgamWitnessCapture:
    if not args.confirm_exact_attachment_rights:
        raise GukgamWitnessPacketError("exact attachment rights confirmation is required")
    packet = load_packet(args)
    proof = verify_witness_artifact(packet, args.artifact.read_bytes())
    return build_reviewed_gukgam_witness_capture(packet, artifact=proof)


def persist_capture(repository: Application, capture: ReviewedGukgamWitnessCapture) -> dict:
    # Verify again before even a SourceRun write; no DRAFT packet can leave a run/checkpoint.
    capture = build_reviewed_gukgam_witness_capture(capture.packet, artifact=capture.artifact)
    run = repository.acquisition.start_source_run(
        GUKGAM_WITNESS_FEEDER, capture.scope_key, metadata=capture.run_metadata,
    )
    try:
        committed = repository.acquisition.commit_source_page(
            run_id=run.id, policy=capture.policy, source=capture.source,
            snapshot=capture.snapshot, observations=capture.observations(run.id),
            cursor=capture.cursor, checkpoint_metadata=capture.run_metadata,
        )
        finished = repository.acquisition.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    except (OSError, RuntimeError, SQLAlchemyError, ValueError):
        repository.acquisition.finish_source_run(
            run.id, SourceRunStatus.FAILED, error_code="GUKGAM_WITNESS_IMPORT_FAILED",
            error_summary="Reviewed witness acquisition failed.",
        )
        raise
    return inspection((capture.packet,)) | {
        "status": "COMMITTED", "artifact_bytes_verified": True, "run_id": str(finished.id),
        "snapshot_id": str(committed.snapshot_id),
        "observations_created": committed.observations_created,
        "observations_unchanged": committed.observations_unchanged,
    }
