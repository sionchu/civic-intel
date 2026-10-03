from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.gukgam_witness_packet import (
    GukgamWitnessPacketError,
    parse_reviewed_gukgam_witness_packet,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.gukgam_witness_import import (
    GUKGAM_WITNESS_FEEDER,
    GukgamWitnessCapture,
    GukgamWitnessImportError,
    build_gukgam_witness_capture,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate (default) or persist one exact human-reviewed Gukgam witness-list "
            "packet as Source/SourceSnapshot/FeederObservation rows. Never creates People, "
            "Organizations, Claims or identity links."
        )
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--confirm-exact-attachment-rights",
        action="store_true",
        help="Confirm that the exact attachment's metadata reuse rights were reviewed.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write to the database. Without it nothing is written.",
    )
    return parser


def _load_capture(args: argparse.Namespace) -> GukgamWitnessCapture:
    if not args.confirm_exact_attachment_rights:
        raise GukgamWitnessImportError("--confirm-exact-attachment-rights is required")
    packet = parse_reviewed_gukgam_witness_packet(
        json.loads(args.packet.read_text(encoding="utf-8"))
    )
    return build_gukgam_witness_capture(
        packet, artifact_bytes=args.artifact.read_bytes()
    )


def _safe_report(capture: GukgamWitnessCapture) -> dict[str, object]:
    source = capture.packet.source
    return {
        "feeder": GUKGAM_WITNESS_FEEDER,
        "committee_name": source.committee_name,
        "list_version": source.list_version,
        "adoption_date": source.adoption_date.isoformat(),
        "attachment_sha256": source.attachment_sha256,
        "reviewed_packet_hash": capture.packet_hash,
        "witness_rows": sum(1 for r in capture.packet.rows if r.category == "증인"),
        "reference_person_rows": sum(
            1 for r in capture.packet.rows if r.category == "참고인"
        ),
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
        GukgamWitnessPacketError,
        GukgamWitnessImportError,
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
        GUKGAM_WITNESS_FEEDER, capture.scope_key, metadata=capture.run_metadata
    )
    try:
        committed = repository.commit_source_page(
            run_id=run.id,
            policy=capture.policy,
            source=capture.source,
            snapshot=capture.snapshot,
            observations=capture.observations(run.id),
            cursor=capture.cursor,
            checkpoint_metadata=capture.checkpoint_metadata,
        )
        finished = repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
    except (OSError, RuntimeError, SQLAlchemyError, ValueError) as exc:
        repository.finish_source_run(
            run.id,
            SourceRunStatus.FAILED,
            error_code="GUKGAM_WITNESS_PACKET_IMPORT_FAILED",
            error_summary=type(exc).__name__,
        )
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
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
