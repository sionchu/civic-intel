"""Batch reviewed Gazette member-total links from an owner-reviewed roster match CSV.

Preview is the default and writes only an owner-local preview JSON; nothing is written to the
database. Commit replays the exact same canonical LINK_PERSON commands through the shared admin
workflow and requires the aggregate state hash printed by the preview. Each command creates only
an IdentityReviewItem, a REVIEWED_LINK and one DRAFT declared-total Claim; publication remains
the separate canonical PUBLISH command. The first failure stops the run; nothing is skipped.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.exc import SQLAlchemyError

from packages.domain.admin import AdminAction, AdminCommand
from packages.domain.enums import EvidenceStance
from packages.persistence import SqlAlchemyRepository
from packages.persistence.admin_workflow import AdminError, digest
from packages.verification.assembly_asset_import import (
    ASSEMBLY_ASSET_FEEDER,
    RECORD_KIND_MEMBER_TOTAL,
)

MATCH_CLASS = "UNIQUE_ROSTER_MATCH"
REQUIRED_COLUMNS = ("printed_name", "mona", "person_id", "match_class")
ROSTER_CONTRACT = "assembly_member_roster"
_REQUEST_NAMESPACE = UUID("6b1f3c2a-5d7e-4f80-9a1b-2c3d4e5f6a7b")


class GazetteLinkBatchError(ValueError):
    def __init__(self, code: str, row_number: int | None = None):
        self.code = code
        self.row_number = row_number
        super().__init__(code)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Preview (default) or commit reviewed LINK_PERSON commands for National Assembly "
            "Gazette member declared totals from an owner-reviewed roster match CSV."
        )
    )
    parser.add_argument("--matches", type=Path, required=True,
        help="CSV with printed_name, mona, person_id, match_class columns")
    parser.add_argument("--scope-key", required=True, help="Gazette scope, e.g. gazette:<issue>:pdf:<pdf_id>")
    parser.add_argument("--reason", required=True, help="Owner review reason recorded on every link")
    parser.add_argument("--confirm-human-reviewed-matches", action="store_true",
        help="Owner attests each UNIQUE_ROSTER_MATCH row was human-reviewed")
    parser.add_argument("--preview-output", type=Path, help="New owner-local preview JSON file")
    parser.add_argument("--commit", action="store_true", help="Write. Without it nothing is written.")
    parser.add_argument("--actor", help="Non-secret operator audit identifier")
    parser.add_argument("--state-hash", help="Exact aggregate state hash from the preview")
    parser.add_argument("--database-env", default="CIVIC_DATABASE_URL")
    return parser


def _read_matches(path: Path) -> tuple[list[tuple[int, dict[str, str]]], Counter[str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or any(column not in reader.fieldnames for column in REQUIRED_COLUMNS):
            raise GazetteLinkBatchError("MATCH_CSV_COLUMNS_REQUIRED")
        selected: list[tuple[int, dict[str, str]]] = []
        classes: Counter[str] = Counter()
        for number, row in enumerate(reader, start=2):
            match_class = (row.get("match_class") or "").strip()
            classes[match_class] += 1
            if match_class == MATCH_CLASS:
                selected.append((number, {key: (row.get(key) or "").strip() for key in REQUIRED_COLUMNS}))
    if not selected:
        raise GazetteLinkBatchError("NO_UNIQUE_ROSTER_MATCH_ROWS")
    return selected, classes


def _roster_anchor(repository: SqlAlchemyRepository, person_id: UUID, mona: str, row_number: int) -> UUID:
    """One published current roster Evidence for this Person and exact member code."""
    candidates: list[tuple[bool, str, str, UUID]] = []
    for claim in repository.claims(person_id, published_only=True, current_only=True):
        if (claim.qualifiers.get("source_contract") != ROSTER_CONTRACT
                or claim.qualifiers.get("provider_record_key") != mona):
            continue
        for item in repository.evidence_for(claim.id):
            if item.stance == EvidenceStance.SUPPORT and item.feeder_observation_id is not None:
                candidates.append((claim.predicate != "ASSEMBLY_PARTY", claim.predicate, str(item.id), item.id))
    if not candidates:
        raise GazetteLinkBatchError("GAZETTE_ROSTER_ANCHOR_NOT_FOUND", row_number)
    return min(candidates)[3]


def build_commands(
    repository: SqlAlchemyRepository, matches: list[tuple[int, dict[str, str]]], scope_key: str,
    reason: str,
) -> list[tuple[int, AdminCommand]]:
    totals: dict[str, list[Any]] = {}
    for observation in repository.feeder_observations(ASSEMBLY_ASSET_FEEDER, scope_key):
        if observation.normalized.get("record_kind") == RECORD_KIND_MEMBER_TOTAL:
            totals.setdefault(str(observation.normalized.get("printed_member_name")), []).append(observation)
    if not totals:
        raise GazetteLinkBatchError("GAZETTE_SCOPE_HAS_NO_MEMBER_TOTALS")
    commands: list[tuple[int, AdminCommand]] = []
    seen_observations: set[UUID] = set()
    seen_people: set[UUID] = set()
    for number, row in matches:
        try:
            person_id = UUID(row["person_id"])
        except ValueError:
            raise GazetteLinkBatchError("PERSON_ID_INVALID", number) from None
        if not row["printed_name"] or not row["mona"]:
            raise GazetteLinkBatchError("PRINTED_NAME_AND_MONA_REQUIRED", number)
        candidates = totals.get(row["printed_name"], [])
        if len(candidates) != 1:
            raise GazetteLinkBatchError("GAZETTE_MEMBER_TOTAL_NOT_UNIQUE", number)
        observation = candidates[0]
        stated = observation.normalized.get("reviewer_stated_mona_cd")
        if stated is not None and stated != row["mona"]:
            raise GazetteLinkBatchError("GAZETTE_MONA_CONFLICT", number)
        if observation.id in seen_observations or person_id in seen_people:
            raise GazetteLinkBatchError("DUPLICATE_MATCH_ROW", number)
        seen_observations.add(observation.id)
        seen_people.add(person_id)
        evidence_id = _roster_anchor(repository, person_id, row["mona"], number)
        request_id = uuid5(_REQUEST_NAMESPACE, "|".join(
            (str(observation.id), str(person_id), str(evidence_id), reason)))
        commands.append((number, AdminCommand(request_id=request_id, action=AdminAction.LINK_PERSON,
            record_ids=(observation.id,), target_person_id=person_id, evidence_ids=(evidence_id,),
            reason=reason, identity_basis="PUBLIC_DISCLOSURE_SOURCE_CONTEXT", human_verified=True)))
    return commands


def aggregate_state_hash(entries: list[dict[str, Any]]) -> str:
    return digest([{key: entry[key] for key in ("request_id", "command_hash", "state_hash")}
                   for entry in entries])


def _emit(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_human_reviewed_matches:
        parser.error("--confirm-human-reviewed-matches is required")
    if args.commit:
        if not args.actor or not args.state_hash:
            parser.error("--actor and --state-hash are required with --commit")
    elif args.preview_output is None:
        parser.error("--preview-output is required for preview")
    database_url = os.environ.get(args.database_env)
    if not database_url:
        parser.error(f"Configured database environment {args.database_env} is required")
    repository = SqlAlchemyRepository(database_url)
    report: dict[str, Any] = {"status": "PREVIEW", "write_performed": False,
        "scope_key": args.scope_key, "feeder": ASSEMBLY_ASSET_FEEDER,
        "claim_publication": False, "asset_disclosure_materialization": False}
    entries: list[dict[str, Any]] = []
    try:
        matches, classes = _read_matches(args.matches)
        report["match_class_counts"] = dict(sorted(classes.items()))
        commands = build_commands(repository, matches, args.scope_key, args.reason)
        for number, command in commands:
            try:
                preview = repository.admin_preview(command)
            except AdminError as exc:
                raise GazetteLinkBatchError(exc.code, number) from None
            entries.append({"row_number": number, "request_id": str(command.request_id),
                "observation_id": str(command.record_ids[0]),
                "person_id": str(command.target_person_id),
                "evidence_id": str(command.evidence_ids[0]),
                "command_hash": preview["command_hash"], "state_hash": preview["state_hash"],
                "preview": preview})
        aggregate = aggregate_state_hash(entries)
        report.update(selected_count=len(entries), aggregate_state_hash=aggregate)
        if not args.commit:
            with args.preview_output.open("x", encoding="utf-8") as output:
                json.dump({"aggregate_state_hash": aggregate, "scope_key": args.scope_key,
                    "commands": [command.model_dump(mode="json") for _, command in commands],
                    "rows": entries}, output, ensure_ascii=False, indent=2, sort_keys=True)
            _emit(report)
            return 0
        if aggregate != args.state_hash:
            raise GazetteLinkBatchError("STALE_AGGREGATE_PREVIEW")
        committed: list[str] = []
        report.update(status="COMMITTING", committed_request_ids=committed)
        for (number, command), entry in zip(commands, entries, strict=True):
            try:
                repository.admin_commit(command, actor=args.actor, state_hash=entry["state_hash"])
            except AdminError as exc:
                raise GazetteLinkBatchError(exc.code, number) from None
            committed.append(str(command.request_id))
            report["write_performed"] = True
        report["status"] = "COMMITTED"
        _emit(report)
        return 0
    except GazetteLinkBatchError as exc:
        report.update(status="FAILED", error_code=exc.code, failed_row_number=exc.row_number)
    except FileExistsError:
        report.update(status="FAILED", error_code="PREVIEW_OUTPUT_EXISTS")
    except (OSError, ValueError, SQLAlchemyError) as exc:
        report.update(status="FAILED", error_code=type(exc).__name__)
    _emit(report)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
