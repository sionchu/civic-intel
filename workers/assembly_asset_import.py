from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.assembly_asset_packet import (
    VALUE_SEMANTICS,
    AssemblyAssetPacketError,
    parse_reviewed_assembly_asset_packet,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.assembly_asset_import import (
    ASSEMBLY_ASSET_FEEDER,
    AssemblyAssetCapture,
    AssemblyAssetImportError,
    build_assembly_asset_capture,
    effective_gazette_policy,
    gazette_asset_policy,
)
from packages.verification.policy import PolicyDenied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate (default) or persist one exact human-reviewed National Assembly Gazette "
            "asset-disclosure packet as Source/SourceSnapshot/FeederObservation rows. Never "
            "fetches, and never creates People, AssetDisclosures, Claims or identity links."
        )
    )
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True, help="operator-saved Gazette PDF")
    parser.add_argument("--database-url")
    parser.add_argument(
        "--confirm-gazette-rights-review",
        action="store_true",
        help="Confirm the owner reviewed reuse rights for this exact Gazette issue.",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write to the database. Without it nothing is written.",
    )
    return parser


def _safe_report(capture: AssemblyAssetCapture) -> dict[str, object]:
    source = capture.packet.source
    return {
        "feeder": ASSEMBLY_ASSET_FEEDER,
        "gazette_issue": source.gazette_issue,
        "pdf_id": source.pdf_id,
        "disclosure_kind": source.disclosure_kind,
        "coverage": capture.packet.coverage,
        "artifact_sha256": source.artifact_sha256,
        "reviewed_packet_hash": capture.packet_hash,
        "member_count": len(capture.packet.members),
        "self_item_count": capture.self_item_count,
        "excluded_relative_item_count": capture.excluded_relative_item_count,
        "value_semantics": VALUE_SEMANTICS,
        "fulltext_retained": False,
        "person_materialization": False,
        "asset_disclosure_materialization": False,
        "claim_publication": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_gazette_rights_review:
        parser.error("--confirm-gazette-rights-review is required")
    if args.commit and not args.database_url:
        parser.error("--database-url is required with --commit")
    repository = SqlAlchemyRepository(args.database_url) if args.database_url else None
    try:
        stored = repository.policies().values() if repository else ()
        policy = effective_gazette_policy(stored)
        packet = parse_reviewed_assembly_asset_packet(
            json.loads(args.packet.read_text(encoding="utf-8"))
        )
        capture = build_assembly_asset_capture(
            packet, artifact_bytes=args.artifact.read_bytes(), policy=policy
        )
    except (
        AssemblyAssetPacketError,
        AssemblyAssetImportError,
        PolicyDenied,
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
    assert repository is not None
    assert capture.policy.id == gazette_asset_policy().id

    run = repository.start_source_run(
        ASSEMBLY_ASSET_FEEDER, capture.scope_key, metadata=capture.run_metadata
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
            error_code="ASSEMBLY_ASSET_PACKET_IMPORT_FAILED",
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
