from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.connectors.gukgam_reviewed_packet import (
    GukgamReviewedPacketError,
    parse_reviewed_gukgam_plan_packet,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.gukgam_reviewed_plan_import import (
    EXACT_ATTACHMENT_RIGHTS,
    GUKGAM_REVIEWED_PLAN_FEEDER,
    GukgamReviewedPlanImportError,
    ReviewedGukgamArtifactProof,
    build_reviewed_gukgam_plan_capture,
    validate_reviewed_gukgam_capture_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or persist one exact human-reviewed Gukgam plan attachment without "
            "creating People, Organizations, Claims, or identity links."
        )
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--attachment-url", required=True)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--confirm-exact-attachment-rights",
        action="store_true",
        help="Confirm that the exact attachment's metadata reuse rights were reviewed.",
    )
    parser.add_argument("--commit", action="store_true")
    return parser


def _load_capture(args: argparse.Namespace):
    if not args.confirm_exact_attachment_rights:
        raise GukgamReviewedPlanImportError(
            "--confirm-exact-attachment-rights is required"
        )
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
        "audited_target_mentions": sum(
            len(row.audited_targets) for row in capture.packet.schedule
        ),
        "source_host": capture.policy.domain,
        "fulltext_retained": False,
        "person_materialization": False,
        "organization_materialization": False,
        "claim_publication": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        capture = _load_capture(args)
    except (
        GukgamReviewedPacketError,
        GukgamReviewedPlanImportError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        parser.error(str(exc))

    if not args.commit:
        print(
            json.dumps(
                {"status": "DRY_RUN"} | _safe_report(capture),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    if not args.database_url:
        parser.error("--database-url is required with --commit")

    repository = SqlAlchemyRepository(args.database_url)
    run = repository.start_source_run(
        GUKGAM_REVIEWED_PLAN_FEEDER,
        capture.scope_key,
        metadata=capture.run_metadata,
    )
    try:
        observations = capture.observations(run.id)
        committed = repository.commit_source_page(
            run_id=run.id,
            policy=capture.policy,
            source=capture.source,
            snapshot=capture.snapshot,
            observations=observations,
            cursor=capture.cursor,
            checkpoint_metadata=capture.checkpoint_metadata,
        )
        finished = repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    except Exception as exc:
        try:
            repository.finish_source_run(
                run.id,
                SourceRunStatus.FAILED,
                error_code="GUKGAM_REVIEWED_PACKET_IMPORT_FAILED",
                error_summary=type(exc).__name__,
            )
        except Exception:
            pass
        raise

    print(
        json.dumps(
            {
                "status": "COMMITTED",
                **_safe_report(capture),
                "run_id": str(finished.id),
                "snapshot_id": str(committed.snapshot_id),
                "observations_created": committed.observations_created,
                "observations_unchanged": committed.observations_unchanged,
                "observation_ids": [str(item) for item in committed.observation_ids],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
