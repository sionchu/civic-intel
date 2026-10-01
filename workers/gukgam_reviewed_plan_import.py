from __future__ import annotations

import argparse
import json

from sqlalchemy.exc import SQLAlchemyError

from packages.application.context import Application
from packages.connectors.gukgam_reviewed_packet import parse_reviewed_gukgam_plan_packet
from packages.domain.enums import SourceRunStatus
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    GUKGAM_REVIEWED_PLAN_FEEDER,
    GukgamReviewedPlanImportError,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
    validate_reviewed_gukgam_capture_metadata,
)


def _load_capture(args: argparse.Namespace):
    if not args.confirm_exact_attachment_rights:
        raise GukgamReviewedPlanImportError("--confirm-exact-attachment-rights is required")
    packet_raw = json.loads(args.packet.read_text(encoding="utf-8"))
    packet = parse_reviewed_gukgam_plan_packet(packet_raw)
    artifact_bytes = args.artifact.read_bytes()
    proof = ReviewedGukgamArtifactProof.from_bytes(
        packet,
        attachment_url=args.attachment_url,
        artifact_bytes=artifact_bytes,
        rights_scope=EXACT_ATTACHMENT_RIGHTS,
    )
    capture = build_reviewed_gukgam_plan_capture(packet, artifact=proof)
    validate_reviewed_gukgam_capture_metadata(capture.snapshot.metadata)
    return capture


def _safe_report(capture) -> dict[str, object]:
    return {
        "feeder": GUKGAM_REVIEWED_PLAN_FEEDER,
        "committee_name": capture.packet.source.committee_name,
        "ntt_id": capture.packet.source.ntt_id,
        "attachment_sha256": capture.artifact.attachment_sha256,
        "reviewed_packet_hash": capture.packet_hash,
        "schedule_rows": len(capture.packet.schedule),
        "audited_target_mentions": sum(len(row.audited_targets) for row in capture.packet.schedule),
        "source_host": capture.policy.domain,
        "fulltext_retained": False,
        "person_materialization": False,
        "organization_materialization": False,
        "claim_publication": False,
    }


def persist_capture(repository: Application, capture) -> dict:
    run = repository.acquisition.start_source_run(
        GUKGAM_REVIEWED_PLAN_FEEDER, capture.scope_key, metadata=capture.run_metadata
    )
    try:
        observations = capture.observations(run.id)
        committed = repository.acquisition.commit_source_page(
            run_id=run.id,
            policy=capture.policy,
            source=capture.source,
            snapshot=capture.snapshot,
            observations=observations,
            cursor=capture.cursor,
            checkpoint_metadata=capture.checkpoint_metadata,
        )
        finished = repository.acquisition.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    except (OSError, RuntimeError, SQLAlchemyError, ValueError) as exc:
        repository.acquisition.finish_source_run(
            run.id,
            SourceRunStatus.FAILED,
            error_code="GUKGAM_REVIEWED_PACKET_IMPORT_FAILED",
            error_summary=type(exc).__name__,
        )
        raise
    return {
        "status": "COMMITTED",
        **_safe_report(capture),
        "run_id": str(finished.id),
        "snapshot_id": str(committed.snapshot_id),
        "observations_created": committed.observations_created,
        "observations_unchanged": committed.observations_unchanged,
        "observation_ids": [str(item) for item in committed.observation_ids],
    }
