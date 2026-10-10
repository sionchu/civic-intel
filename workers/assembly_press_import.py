"""One supplied, policy-permitted official press metadata page; default no writes.

Input stays operator-local, including when can_send_to_ai is false. No fetch,
article body, automatic Person linkage or implicit publication is performed.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.base import ConnectorDocument
from packages.connectors.open_assembly_activity_metadata import (
    ACTIVITY_APIS,
    LOCATOR_UNVERIFIED,
    require_activity_policy,
)
from packages.connectors.open_assembly_press_releases import OpenAssemblyPressReleaseConnector
from packages.domain.admin import AdminCommand
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.persistence.repository import source_policy_semantics_equal
from packages.verification.assembly_press_import import (
    PRESS_CONTRACT,
    PRESS_FEEDER,
    build_activity_capture,
    build_press_capture,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--activity-api", choices=ACTIVITY_APIS,
        help="Supplied metadata only; stable locator/query semantics remain unverified")
    parser.add_argument("--operation", choices=("capture", "link", "publish"), default="capture")
    parser.add_argument("--command", type=Path)
    parser.add_argument("--preview-output", type=Path)
    parser.add_argument("--database-env", default="CIVIC_DATABASE_URL")
    parser.add_argument("--actor")
    parser.add_argument("--state-hash")
    parser.add_argument("--commit", action="store_true")
    args = parser.parse_args(argv)
    try:
        policy = SourcePolicy.model_validate_json(args.policy.read_text(encoding="utf-8"))
        if args.activity_api:
            require_activity_policy(policy)
        else:
            OpenAssemblyPressReleaseConnector(policy=policy, written_on=date.min)._gate()
        raw = json.loads(args.metadata.read_text(encoding="utf-8"))
        if args.activity_api:
            def capture(run_id: UUID):
                return build_activity_capture(raw, api_code=args.activity_api, policy=policy, run_id=run_id)
        else:
            if not isinstance(raw, dict) or set(raw) != {
            "written_date", "page_index", "page_size", "list_total_count", "records",
            } or type(raw["list_total_count"]) is not int:
                raise ValueError("PRESS_PAGE_FIELDS_INVALID")
            day = date.fromisoformat(raw["written_date"])
            connector = OpenAssemblyPressReleaseConnector(policy=policy, written_on=day,
                page_index=raw["page_index"], page_size=raw["page_size"])
            document = ConnectorDocument(url=connector.discover()[0], title="국회 공식 보도자료",
                publisher="국회사무처", published_at=None, body=json.dumps(raw["records"]),
                metadata={"source_contract": PRESS_CONTRACT,
                    "list_total_count": str(raw["list_total_count"]), "row_count": str(len(raw["records"]))})
            def capture(run_id: UUID):
                return build_press_capture(document, policy=policy, written_on=day,
                    page_index=raw["page_index"], page_size=raw["page_size"], run_id=run_id)
        source, snapshot, observations = capture(uuid4())
        report: dict[str, object] = {"status": "DRY_RUN", "write_performed": False,
            "record_count": len(observations), "snapshot_hash": snapshot.content_hash,
            "coverage": "SELECTED_PAGE_ONLY", "claim_publication": False,
            "identity_review_confirmed": False, "ai_processing": False}
        if args.activity_api:
            report.update(source_api=args.activity_api, record_identity_status=LOCATOR_UNVERIFIED,
                query_semantics="UNVERIFIED_NOT_FETCHED", publication_eligible=False)
        url = os.environ.get(args.database_env)
        repository = SqlAlchemyRepository(url) if url else None
        if args.operation == "capture":
            if args.command:
                parser.error("PRESS_CAPTURE_COMMAND_FORBIDDEN")
            if args.commit:
                if repository is None:
                    parser.error("PRESS_DATABASE_REQUIRED")
                stored = repository.policies().get(policy.id)
                if stored is None or not source_policy_semantics_equal(stored, policy):
                    parser.error("PRESS_STORED_POLICY_MISMATCH")
                scope = observations[0].scope_key if observations else (
                    f"activity:{args.activity_api}:supplied-page:{raw['page_index']}" if args.activity_api
                    else f"press:{day.isoformat()}:selected-pages")
                contract = snapshot.metadata["source_contract"]
                run = repository.start_source_run(PRESS_FEEDER, scope,
                    metadata={"source_contract": contract, "coverage": "SELECTED_PAGE_ONLY"})
                try:
                    source, snapshot, observations = capture(run.id)
                    result = repository.commit_source_page(run_id=run.id, policy=policy,
                        source=source, snapshot=snapshot, observations=observations,
                        cursor=str(raw["page_index"]), require_stored_policy_match=True,
                        checkpoint_metadata={"source_contract": contract,
                            "coverage": "SELECTED_PAGE_ONLY", "list_total_count": raw["list_total_count"]})
                    repository.finish_source_run(run.id, SourceRunStatus.SUCCESS)
                except (ValueError, RuntimeError, SQLAlchemyError):
                    repository.finish_source_run(run.id, SourceRunStatus.FAILED, error_code="PRESS_CAPTURE_FAILED",
                        error_summary="PRESS_CAPTURE_FAILED")
                    raise
                report.update(status="COMMITTED", write_performed=True,
                    observation_ids=[str(i) for i in result.observation_ids],
                    snapshot_id=str(result.snapshot_id))
        else:
            if not args.command or repository is None:
                parser.error("PRESS_COMMAND_DATABASE_REQUIRED")
            command = AdminCommand.model_validate_json(args.command.read_text(encoding="utf-8"))
            expected = "LINK_PERSON" if args.operation == "link" else "PUBLISH"
            if command.action != expected or len(command.record_ids) != 1:
                parser.error("PRESS_SINGLE_RECORD_COMMAND_REQUIRED")
            if expected == "LINK_PERSON":
                if command.identity_basis != "OFFICIAL_PRESS_SOURCE_CONTEXT":
                    parser.error("PRESS_REVIEW_BASIS_REQUIRED")
                selected = repository.feeder_observation(command.record_ids[0])
            else:
                contexts = repository.feeder_observation_contexts([
                    item.feeder_observation_id for item in repository.evidence_for(command.record_ids[0])
                    if item.stance == "SUPPORT" and item.feeder_observation_id is not None])
                selected = next(iter(contexts.values()))[0] if len(contexts) == 1 else None
            if selected is None or not any(selected.feeder == item.feeder
                    and selected.scope_key == item.scope_key
                    and selected.provider_record_key == item.provider_record_key
                    and selected.content_hash == item.content_hash for item in observations):
                parser.error("PRESS_SELECTED_METADATA_MISMATCH")
            preview = repository.admin_preview(command)
            if args.preview_output:
                with args.preview_output.open("x", encoding="utf-8") as output:
                    json.dump(preview, output, ensure_ascii=False, indent=2)
            report.update(status="ADMIN_PREVIEW", state_hash=preview["state_hash"],
                selected_ids=[str(i) for i in command.record_ids],
                identity_review_confirmed=command.human_verified)
            if args.commit:
                if not args.actor or not args.state_hash:
                    parser.error("PRESS_REVIEWED_STATE_REQUIRED")
                repository.admin_commit(command, actor=args.actor, state_hash=args.state_hash)
                report.update(status="ADMIN_COMMITTED", write_performed=True,
                    claim_publication=expected == "PUBLISH")
        print(json.dumps(report, sort_keys=True))
        return 0
    except (OSError, TypeError, ValueError, PermissionError, RuntimeError, SQLAlchemyError):
        parser.error("PRESS_OPERATION_VALIDATION_FAILED")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
