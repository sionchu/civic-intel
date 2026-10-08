from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.assembly_asset_packet import (
    VALUE_SEMANTICS,
    AssemblyAssetPacketError,
    parse_reviewed_assembly_asset_packet,
)
from packages.domain.admin import AdminAction, AdminCommand
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.persistence.repository import source_policy_semantics_equal
from packages.verification.assembly_asset_import import (
    ASSEMBLY_ASSET_FEEDER,
    PETI_ASSET_FEEDER,
    PETI_ASSET_SOURCE_CONTRACT,
    AssemblyAssetCapture,
    AssemblyAssetImportError,
    build_assembly_asset_capture,
    build_peti_asset_capture,
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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--packet", type=Path)
    source.add_argument("--peti-receipt", type=Path)
    parser.add_argument("--artifact", type=Path, help="operator-saved Gazette PDF")
    parser.add_argument("--peti-policy", type=Path)
    parser.add_argument("--peti-operation", choices=("policy", "capture", "link", "publish"), default="capture")
    parser.add_argument("--command", type=Path, help="Explicit reviewed canonical AdminCommand JSON")
    parser.add_argument("--state-hash", help="Exact state hash from canonical admin preview")
    parser.add_argument("--actor", help="Non-secret operator audit identifier")
    parser.add_argument("--preview-output", type=Path, help="New owner-local canonical preview JSON file")
    parser.add_argument("--database-env", default="CIVIC_DATABASE_URL")
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
    if args.peti_receipt:
        return _peti_main(parser, args)
    if args.artifact is None:
        parser.error("--artifact is required for Gazette packets")
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


def _peti_main(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """One supplied metadata record. Identity review and publication use canonical admin audit."""
    if not args.peti_policy or args.artifact or args.confirm_gazette_rights_review or args.database_url:
        parser.error("PETI requires --peti-policy; Gazette options and URL credentials are not accepted")
    try:
        policy = SourcePolicy.model_validate_json(args.peti_policy.read_text(encoding="utf-8"))
        raw = json.loads(args.peti_receipt.read_text(encoding="utf-8"))
        source, snapshot, observation = build_peti_asset_capture(raw, policy=policy, run_id=uuid4())
        database_url = os.environ.get(args.database_env)
        repository = SqlAlchemyRepository(database_url) if database_url else None
        report: dict[str, object] = {"status": "DRY_RUN", "write_performed": False,
            "feeder": PETI_ASSET_FEEDER, "record_count": 1,
            "provider_record_key": observation.provider_record_key,
            "metadata_hash": observation.content_hash, "amount_unit": "THOUSAND_KRW",
            "claim_publication": False, "identity_review_confirmed": False}
        if args.peti_operation == "policy":
            if not args.command or repository is None:
                parser.error("Policy registration preview requires --command and configured database environment")
            command = AdminCommand.model_validate_json(args.command.read_text(encoding="utf-8"))
            if command.action != AdminAction.REGISTER_SOURCE_POLICY or command.value is None:
                parser.error("PETI_POLICY_REGISTRATION_COMMAND_REQUIRED")
            if not source_policy_semantics_equal(SourcePolicy.model_validate_json(command.value), policy):
                parser.error("PETI_POLICY_CANDIDATE_MISMATCH")
            preview = repository.admin_preview(command)
            if args.preview_output:
                with args.preview_output.open("x", encoding="utf-8") as output:
                    json.dump(preview, output, ensure_ascii=False, indent=2, sort_keys=True)
            report.update(status="POLICY_REGISTRATION_PREVIEW", state_hash=preview["state_hash"],
                policy_id=str(policy.id), policy_hash=preview["outcomes"][0]["policy_hash"],
                disposition=preview["outcomes"][0]["disposition"], policy_registration=False)
            if args.commit:
                if not args.actor or not args.state_hash:
                    parser.error("--actor and --state-hash are required for policy registration commit")
                result = repository.admin_commit(command, actor=args.actor, state_hash=args.state_hash)
                changed = bool(result["write_performed"])
                report.update(status="POLICY_REGISTERED" if changed else "POLICY_NO_WRITE",
                    write_performed=changed, policy_registration=changed)
        elif args.peti_operation == "capture":
            if args.command:
                parser.error("Capture does not accept an identity/publication command")
            if args.commit:
                if repository is None:
                    parser.error("Configured database environment is required for --commit")
                stored = repository.policies().get(policy.id)
                if stored is None or not source_policy_semantics_equal(stored, policy):
                    parser.error("PETI_STORED_POLICY_MISMATCH")
                run = repository.start_source_run(PETI_ASSET_FEEDER, observation.scope_key,
                    metadata={"source_contract": PETI_ASSET_SOURCE_CONTRACT, "record_count": 1})
                try:
                    source, snapshot, observation = build_peti_asset_capture(raw, policy=policy, run_id=run.id)
                    committed = repository.commit_source_page(run_id=run.id, policy=policy,
                        source=source, snapshot=snapshot, observations=(observation,), cursor="1",
                        require_stored_policy_match=True,
                        checkpoint_metadata={"source_contract": PETI_ASSET_SOURCE_CONTRACT,
                            "selected_record_count": 1,
                            "seen_provider_hashes": {observation.provider_record_key: observation.content_hash}})
                    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
                except (RuntimeError, SQLAlchemyError, ValueError):
                    repository.finish_source_run(run.id, SourceRunStatus.FAILED,
                        error_code="PETI_CAPTURE_FAILED", error_summary="PETI_CAPTURE_FAILED")
                    raise
                report.update(status="COMMITTED", write_performed=True,
                    observation_ids=[str(value) for value in committed.observation_ids],
                    snapshot_id=str(committed.snapshot_id), observations_created=committed.observations_created,
                    observations_unchanged=committed.observations_unchanged)
        else:
            if not args.command or repository is None:
                parser.error("Link/publication preview requires --command and configured database environment")
            stored = repository.policies().get(policy.id)
            if stored is None or not source_policy_semantics_equal(stored, policy):
                parser.error("PETI_STORED_POLICY_MISMATCH")
            command_raw = json.loads(args.command.read_text(encoding="utf-8"))
            if args.peti_operation == "link" and command_raw.get("human_verified") is not True:
                if args.commit:
                    parser.error("PETI_OWNER_IDENTITY_REVIEW_REQUIRED")
                report.update(status="OWNER_SOURCE_CONTEXT_REVIEW_PENDING",
                    required_action="LINK_PERSON", required_identity_basis="PUBLIC_DISCLOSURE_SOURCE_CONTEXT")
            else:
                command = AdminCommand.model_validate(command_raw)
                expected = AdminAction.LINK_PERSON if args.peti_operation == "link" else AdminAction.PUBLISH
                if command.action != expected or len(command.record_ids) != 1:
                    parser.error("PETI_SINGLE_RECORD_OPERATION_REQUIRED")
                if expected == AdminAction.LINK_PERSON:
                    selected = repository.feeder_observation(command.record_ids[0])
                    if command.identity_basis != "PUBLIC_DISCLOSURE_SOURCE_CONTEXT":
                        parser.error("PETI_SOURCE_CONTEXT_BASIS_REQUIRED")
                else:
                    contexts = repository.feeder_observation_contexts([UUID(str(item.feeder_observation_id))
                        for item in repository.evidence_for(command.record_ids[0]) if item.stance.value == "SUPPORT"])
                    selected = next(iter(contexts.values()))[0] if len(contexts) == 1 else None
                if selected is None or selected.feeder != PETI_ASSET_FEEDER or selected.provider_record_key != observation.provider_record_key or selected.content_hash != observation.content_hash:
                    parser.error("PETI_SELECTED_RECEIPT_MISMATCH")
                preview = repository.admin_preview(command)
                if args.preview_output:
                    with args.preview_output.open("x", encoding="utf-8") as output:
                        json.dump(preview, output, ensure_ascii=False, indent=2, sort_keys=True)
                report.update(status="ADMIN_PREVIEW", state_hash=preview["state_hash"],
                    selected_ids=[str(value) for value in command.record_ids],
                    identity_review_confirmed=command.human_verified)
                if args.commit:
                    if not args.actor or not args.state_hash:
                        parser.error("--actor and --state-hash are required for reviewed admin commit")
                    result = repository.admin_commit(command, actor=args.actor, state_hash=args.state_hash)
                    report.update(status="ADMIN_COMMITTED", write_performed=True,
                        claim_publication=expected == AdminAction.PUBLISH,
                        state_hash=result.get("state_hash", args.state_hash))
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, PermissionError, RuntimeError, SQLAlchemyError):
        parser.error("PETI_OPERATION_VALIDATION_FAILED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
