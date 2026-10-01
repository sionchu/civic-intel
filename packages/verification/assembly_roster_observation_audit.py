"""Validate and export the exact committed National Assembly roster observation set."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

FEEDER = "national_assembly_members"
SCOPE_KEY = "current_member_roster"
SEMANTIC_SCOPE = "legislative_member_roster"


def _result_from_receipt(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    if receipt.get("effect") != "SOURCE_INGESTION" or receipt.get("command") != "observe assembly":
        raise RuntimeError("receipt is not an Assembly source-observation command")
    result = receipt.get("result")
    if not isinstance(result, Mapping):
        raise TypeError("Assembly observation receipt has no result")
    run = result.get("run")
    if not isinstance(run, Mapping):
        raise TypeError("Assembly observation receipt has no source run")
    if run.get("status") != "SUCCESS":
        raise RuntimeError("Assembly roster observation did not finish successfully")
    return result


def current_observations(observations: Sequence[Any], manifest: Mapping[str, str]) -> dict[str, Any]:
    """Resolve the current version for each provider key and enforce exact manifest coverage."""
    current: dict[str, Any] = {}
    for observation in observations:
        expected_hash = manifest.get(observation.provider_record_key)
        if (
            expected_hash is None
            or expected_hash != observation.content_hash
            or observation.semantic_scope != SEMANTIC_SCOPE
        ):
            continue
        if observation.provider_record_key in current:
            raise RuntimeError("Current provider key maps to multiple observations")
        current[observation.provider_record_key] = observation
    if set(current) != set(manifest):
        raise RuntimeError("Current observations do not match the checkpoint provider manifest")
    return current


def build_report(
    receipt: Mapping[str, Any],
    *,
    checkpoint: Any,
    run: Any,
    observations: Sequence[Any],
) -> dict[str, Any]:
    result = _result_from_receipt(receipt)
    if checkpoint is None or checkpoint.last_run_id is None:
        raise RuntimeError("Assembly roster checkpoint is missing after enumeration")
    if str(checkpoint.last_run_id) != str(run.id) or str(result["run"]["id"]) != str(run.id):
        raise RuntimeError("Receipt, successful source run, and checkpoint do not match")
    if run.status.value != "SUCCESS":
        raise RuntimeError("Current checkpoint run is not successful")
    if run.checkpoint_after != checkpoint.cursor:
        raise RuntimeError("Source run and checkpoint cursors do not match")

    metadata = checkpoint.metadata
    from packages.verification.assembly_base_profile import ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT

    if metadata.get("source_contract") != ASSEMBLY_BASE_PROFILE_SOURCE_CONTRACT:
        raise RuntimeError("Assembly checkpoint uses an unexpected source contract")
    manifest = metadata.get("seen_provider_hashes")
    if not isinstance(manifest, dict) or not manifest:
        raise RuntimeError("Assembly provider manifest is empty")
    expected_total = int(metadata["list_total_count"])
    expected_pages = int(metadata["expected_pages"])
    current = current_observations(observations, manifest)
    if len(current) != expected_total or int(result.get("unique_records", -1)) != expected_total:
        raise RuntimeError("Current observation coverage does not match provider total count")
    if run.records_seen != expected_total or (
        run.observations_created + run.observations_unchanged != expected_total
    ):
        raise RuntimeError("Persisted source-run counts do not match provider total count")
    if int(result.get("pages_committed", -1)) != expected_pages:
        raise RuntimeError("Run summary page count does not match checkpoint coverage")

    rows = []
    for provider_key in sorted(current):
        observation = current[provider_key]
        normalized = observation.normalized
        rows.append(
            {
                "provider_record_key": provider_key,
                "observation_id": str(observation.id),
                "snapshot_id": str(observation.snapshot_id),
                "content_hash": observation.content_hash,
                "canonical_name": normalized.get("canonical_name"),
                "aliases": normalized.get("aliases") or [],
                "birth_date": normalized.get("birth_date"),
                "party": normalized.get("party"),
                "district": normalized.get("district"),
                "reelection": normalized.get("reelection"),
                "election_type": normalized.get("election_type"),
                "committees": normalized.get("committees"),
            }
        )

    return {
        "feeder": FEEDER,
        "scope_key": SCOPE_KEY,
        "semantic_scope": SEMANTIC_SCOPE,
        "run_id": str(run.id),
        "status": "SUCCESS",
        "pages_committed": result["pages_committed"],
        "expected_pages": expected_pages,
        "provider_total_count": expected_total,
        "current_observation_count": len(rows),
        "checkpoint_cursor": checkpoint.cursor,
        "materialization_performed": False,
        "rows": rows,
    }


def verify_and_build(database_url: str, receipt_path: Path) -> dict[str, Any]:
    from packages.persistence.database import Database

    database = Database(database_url)
    database.assert_ready()
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        result = _result_from_receipt(receipt)
        from uuid import UUID

        run_id = UUID(str(result["run"]["id"]))
        with database(read_only=True) as uow:
            run = uow.acquisition.source_run(run_id)
            if run is None:
                raise RuntimeError("Assembly source run is missing from the database")
            if run.feeder != FEEDER or run.scope_key != SCOPE_KEY:
                raise RuntimeError("Assembly source run is outside the reviewed scope")
            checkpoint = uow.acquisition.source_checkpoint(FEEDER, SCOPE_KEY)
            observations = uow.acquisition.feeder_observations(FEEDER, SCOPE_KEY)
            return build_report(receipt, checkpoint=checkpoint, run=run, observations=observations)
    finally:
        database.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the current Assembly observation audit.")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = verify_and_build(args.database_url, args.receipt)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
