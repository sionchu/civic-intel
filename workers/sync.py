from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from packages.connectors.open_assembly import (
    AssemblyApiError,
    OpenAssemblyMemberConnector,
)
from packages.domain.contracts import SourceCheckpoint, SourceRun
from packages.persistence import SqlAlchemyRepository
from packages.verification.materialization import MaterializationError
from packages.verification.policy import PolicyDenied
from workers.assembly_roster import (
    AssemblyRosterEnumerator,
    AssemblyRosterMaterializationResult,
)

ASSEMBLY_ROSTER_SOURCE = "assembly-roster"


@dataclass(frozen=True)
class AcquisitionSyncReceipt:
    """Transient operational receipt for one source-specific sync invocation."""

    source: str
    scope_key: str
    run: SourceRun
    checkpoint: SourceCheckpoint
    materialization_outcomes: dict[str, int]
    source_alias: str = ASSEMBLY_ROSTER_SOURCE
    resume_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        review_count = self.materialization_outcomes.get("REVIEW_REQUIRED", 0)
        conflict_count = self.materialization_outcomes.get("HARD_CONFLICT", 0)
        return {
            "source": self.source,
            "source_alias": self.source_alias,
            "scope": self.scope_key,
            "run_id": str(self.run.id),
            "started_at": self.run.started_at.isoformat(),
            "finished_at": self.run.finished_at.isoformat()
            if self.run.finished_at is not None
            else None,
            "status": self.run.status.value,
            "source_run_status": self.run.status.value,
            "observed_count": self.run.records_seen,
            "committed_count": self.run.observations_created,
            "unchanged_count": self.run.observations_unchanged,
            "conflict_review_count": review_count + conflict_count,
            "review_required_count": review_count,
            "hard_conflict_count": conflict_count,
            "materialization_outcomes": self.materialization_outcomes,
            "checkpoint": self.checkpoint.cursor,
            "resume_requested": self.resume_requested,
            "error_reason": None,
        }


def run_assembly_roster_sync(
    connector: OpenAssemblyMemberConnector,
    repository: SqlAlchemyRepository,
    *,
    resume: bool = False,
) -> AcquisitionSyncReceipt:
    """Run the existing complete Assembly path behind the smallest sync boundary."""

    result: AssemblyRosterMaterializationResult = AssemblyRosterEnumerator(
        connector,
        repository,
    ).enumerate_and_materialize(resume=resume)
    checkpoint = repository.source_checkpoint(
        AssemblyRosterEnumerator.FEEDER,
        AssemblyRosterEnumerator.SCOPE_KEY,
    )
    if checkpoint is None:
        raise RuntimeError("successful Assembly sync did not leave a checkpoint")
    return AcquisitionSyncReceipt(
        source=AssemblyRosterEnumerator.FEEDER,
        scope_key=AssemblyRosterEnumerator.SCOPE_KEY,
        run=result.enumeration.run,
        checkpoint=checkpoint,
        materialization_outcomes=result.outcome_counts(),
        resume_requested=resume,
    )


def _failure_phase(error: Exception) -> str:
    if isinstance(error, PolicyDenied):
        return "policy"
    if isinstance(error, MaterializationError):
        return "publication"
    if isinstance(error, AssemblyApiError):
        return "source_fetch_parse_or_coverage"
    if isinstance(error, (SQLAlchemyError, RuntimeError, ValueError)):
        return "database_or_precondition"
    return "unexpected"


def _failed_receipt(
    repository: SqlAlchemyRepository | None,
    *,
    prior_run_ids: set[str],
    error: Exception,
    resume: bool,
) -> dict[str, Any]:
    run: SourceRun | None = None
    checkpoint: SourceCheckpoint | None = None
    if repository is not None:
        try:
            runs = repository.source_runs(
                AssemblyRosterEnumerator.FEEDER,
                AssemblyRosterEnumerator.SCOPE_KEY,
            )
            new_runs = [item for item in runs if str(item.id) not in prior_run_ids]
            if new_runs:
                run = max(new_runs, key=lambda item: (item.started_at, str(item.id)))
            if run is not None:
                checkpoint = repository.source_checkpoint(
                    AssemblyRosterEnumerator.FEEDER,
                    AssemblyRosterEnumerator.SCOPE_KEY,
                )
        except (OSError, SQLAlchemyError, RuntimeError, ValueError):
            run = None
            checkpoint = None

    return {
        "source": AssemblyRosterEnumerator.FEEDER,
        "source_alias": ASSEMBLY_ROSTER_SOURCE,
        "scope": AssemblyRosterEnumerator.SCOPE_KEY,
        "run_id": str(run.id) if run is not None else None,
        "started_at": run.started_at.isoformat() if run is not None else None,
        "finished_at": (
            run.finished_at.isoformat()
            if run is not None and run.finished_at is not None
            else None
        ),
        "status": "FAILED",
        "source_run_status": run.status.value if run is not None else None,
        "observed_count": run.records_seen if run is not None else 0,
        "committed_count": run.observations_created if run is not None else 0,
        "unchanged_count": run.observations_unchanged if run is not None else 0,
        "conflict_review_count": None,
        "review_required_count": None,
        "hard_conflict_count": None,
        "materialization_outcomes": None,
        "checkpoint": checkpoint.cursor if checkpoint is not None else None,
        "resume_requested": resume,
        "error_reason": {
            "phase": _failure_phase(error),
            "code": type(error).__name__[:120],
            "summary": "sync did not complete; see the source run status and checkpoint",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one bounded Civic Intel source synchronization boundary."
    )
    parser.add_argument(
        "source",
        choices=(ASSEMBLY_ROSTER_SOURCE,),
        help="source-specific sync boundary",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume the source from its latest committed checkpoint",
    )
    parser.add_argument("--database-url")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repository = SqlAlchemyRepository(args.database_url)
    prior_run_ids: set[str] = set()
    try:
        prior_run_ids = {
            str(item.id)
            for item in repository.source_runs(
                AssemblyRosterEnumerator.FEEDER,
                AssemblyRosterEnumerator.SCOPE_KEY,
            )
        }
        receipt = run_assembly_roster_sync(
            OpenAssemblyMemberConnector(page_size=100),
            repository,
            resume=args.resume,
        )
    except Exception as error:  # noqa: BLE001 - CLI boundary must emit a redacted receipt
        print(
            json.dumps(
                _failed_receipt(
                    repository,
                    prior_run_ids=prior_run_ids,
                    error=error,
                    resume=args.resume,
                ),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(
        json.dumps(
            receipt.to_dict(),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
