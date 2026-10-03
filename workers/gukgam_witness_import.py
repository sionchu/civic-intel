"""One local witness attachment: DRAFT preparation or reviewed acquisition; no crawler."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from packages.application.context import Application
from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacket,
    GukgamWitnessPacketError,
    canonical_hash,
    parse_gukgam_witness_packet,
    parse_gukgam_witness_research,
)
from packages.domain.enums import SourceRunStatus
from packages.rendering.gukgam_witness_plan_review import build_gukgam_witness_plan_review
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    ReviewedGukgamWitnessCapture,
    build_gukgam_witness_draft_edits,
    build_reviewed_gukgam_witness_capture,
    prepare_gukgam_witness_draft,
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


def _write_preparation(path: Path, payload: dict[str, object]) -> None:
    # Exclusive creation preserves inputs, earlier outputs and symlink targets.
    body = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(body)


def inspect_inputs(args: argparse.Namespace) -> dict[str, object]:
    if args.research:
        packets = parse_gukgam_witness_research(
            json.loads(args.research.read_text(encoding="utf-8"))
        )
        artifact_verified = False
    else:
        packet = load_packet(args)
        proof = verify_witness_artifact(packet, args.artifact.read_bytes())
        packets = (packet,)
        artifact_verified = True
    result = inspection(packets) | {"artifact_bytes_verified": artifact_verified}
    if args.write_draft_edits:
        edits = build_gukgam_witness_draft_edits(packet, artifact=proof)
        _write_preparation(args.write_draft_edits, edits)
        result["draft_preparation"] = {
            "status": "LOCAL_DRAFT_EDITS_WRITTEN", "edit_manifest_hash": canonical_hash(edits),
            "row_count": len(packet.rows), "human_attestation": False,
        }
    elif args.draft_edits:
        edits = json.loads(args.draft_edits.read_text(encoding="utf-8"))
        draft = prepare_gukgam_witness_draft(packet, edits, artifact=proof)
        _write_preparation(args.draft_packet, draft.normalized())
        originals = {row.record_key: row for row in packet.rows}
        result["draft_preparation"] = {
            "status": "LOCAL_DRAFT_PACKET_WRITTEN", "packet_hash": draft.content_hash,
            "edit_manifest_hash": canonical_hash(edits), "review_status": draft.review_status,
            "selection": draft.selection, "selected_rows": len(draft.rows),
            "dropped_rows": len(packet.rows) - len(draft.rows),
            "changed_rows": sum(row != originals[row.record_key] for row in draft.rows),
            "human_attestation": False,
        }
    if args.plan_packet:
        plans = [parse_reviewed_gukgam_plan_packet(json.loads(path.read_text(encoding="utf-8")))
                 for path in args.plan_packet]
        result["plan_linkage_review"] = build_gukgam_witness_plan_review(packets, plans)
    return result


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
