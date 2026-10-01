"""Check the installed CLI's safe missing-key failure and durable failed SourceRun."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

FEEDER = "national_assembly_members"
SCOPE_KEY = "current_member_roster"


def validate_failure(receipt: Mapping[str, Any], *, exit_code: int, run: Any, checkpoint: Any) -> None:
    if exit_code != 1:
        raise RuntimeError("missing-key observation command did not return the expected failure code")
    if receipt != {
        "command": "observe assembly",
        "effect": "SOURCE_INGESTION",
        "error_code": "COMMAND_FAILED",
        "status": "FAILED",
    }:
        raise RuntimeError("CLI failure receipt is not the expected redacted contract")
    if run is None or run.feeder != FEEDER or run.scope_key != SCOPE_KEY:
        raise RuntimeError("failed Assembly SourceRun was not persisted")
    if run.status.value != "FAILED" or run.checkpoint_after is not None:
        raise RuntimeError("Assembly SourceRun has an unexpected terminal state or checkpoint")
    if run.error_code != "MissingAssemblyApiKey":
        raise RuntimeError("failed Assembly SourceRun has an unexpected error code")
    summary = (run.error_summary or "").casefold()
    if any(marker in summary for marker in ("api_key", "token=", "key=", "password=")):
        raise RuntimeError("failed Assembly SourceRun summary is not redacted")
    if run.records_seen or run.observations_created or run.observations_unchanged:
        raise RuntimeError("failed Assembly SourceRun committed observations")
    if checkpoint is not None:
        raise RuntimeError("missing-key smoke unexpectedly advanced a source checkpoint")


def verify(database_url: str, receipt_path: Path, exit_code: int) -> None:
    from packages.persistence.database import Database

    database = Database(database_url)
    database.assert_ready()
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        with database(read_only=True) as uow:
            runs = uow.acquisition.source_runs(FEEDER, SCOPE_KEY)
            if len(runs) != 1:
                raise RuntimeError("runtime smoke database does not contain exactly one source run")
            run = runs[-1] if runs else None
            checkpoint = uow.acquisition.source_checkpoint(FEEDER, SCOPE_KEY)
            validate_failure(receipt, exit_code=exit_code, run=run, checkpoint=checkpoint)
    finally:
        database.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate missing-key CLI failure behavior.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    args = parser.parse_args(argv)
    verify(args.database_url, args.receipt, args.exit_code)
    print("assembly-missing-key-smoke=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
