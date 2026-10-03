"""Aggregate operational state; no provider rows, source coverage or identity verdicts."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from packages.domain.enums import SourceRunStatus


def _count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("invalid collection aggregate")
    return value


def _timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("invalid collection timestamp")
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def build_collection_status(
    summary: dict[str, Any], *, running_age_minutes: int = 60, now: datetime | None = None
) -> dict[str, Any]:
    if not 1 <= running_age_minutes <= 10080:
        raise ValueError("running age must be 1 to 10080 minutes")
    observed = now or datetime.now(UTC)
    if observed.tzinfo is None:
        raise ValueError("monitor time requires a timezone")
    observed = observed.astimezone(UTC)
    counts = {key: _count(summary["counts"][key]) for key in (
        "people", "organizations", "claims", "evidence", "sources", "snapshots",
        "observations", "observation_keys", "runs", "checkpoints", "running_runs",
    )}
    lanes = []
    attention = False
    for row in summary["lanes"]:
        raw_status = row["latest_run_status"]
        status = raw_status if raw_status in {s.value for s in SourceRunStatus} else "NO_RUN"
        if raw_status is not None and status == "NO_RUN":
            status = "UNRECOGNIZED"
        started = _timestamp(row["latest_run_started_at"])
        finished = _timestamp(row["latest_run_finished_at"])
        success = _timestamp(row["last_success_at"])
        checkpoint_at = _timestamp(row["checkpoint_updated_at"])
        reasons = []
        if status in {"FAILED", "PARTIAL", "UNRECOGNIZED"}:
            reasons.append("LATEST_RUN_REQUIRES_REVIEW")
        age = None
        if status == "RUNNING":
            if started is None:
                reasons.append("RUN_START_UNAVAILABLE")
            else:
                age = round((observed - started).total_seconds() / 60, 2)
                if age < 0:
                    reasons.append("RUN_START_IN_FUTURE")
                elif age >= running_age_minutes:
                    reasons.append("RUN_AGE_THRESHOLD_EXCEEDED")
            if finished is not None:
                reasons.append("RUNNING_WITH_FINISH_TIME")
        elif status in {"SUCCESS", "PARTIAL", "FAILED"} and finished is None:
            reasons.append("FINISH_TIME_UNAVAILABLE")
        if not row["has_checkpoint"]:
            relation = "NO_CHECKPOINT"
        elif row["checkpoint_run_id"] is None:
            relation = "LINEAGE_UNAVAILABLE"
            reasons.append("CHECKPOINT_LINEAGE_UNAVAILABLE")
        elif not row["checkpoint_run_exists"] or not row["checkpoint_run_scope_matches"]:
            relation = "INVALID_REFERENCE"
            reasons.append("CHECKPOINT_REFERENCE_INVALID")
        else:
            relation = (
                "LATEST_RUN" if row["checkpoint_run_id"] == row["latest_run_id"] else "PRIOR_RUN"
            )
            if row["checkpoint_cursor_matches_run"] is False:
                reasons.append("CHECKPOINT_CURSOR_MISMATCH")
            elif row["checkpoint_cursor_matches_run"] is None:
                reasons.append("CHECKPOINT_CURSOR_COMPARISON_UNAVAILABLE")
        attention |= bool(reasons)
        lanes.append({
            "lane_sha256": hashlib.sha256(
                (row["feeder"] + "\0" + row["scope_key"]).encode("utf-8")
            ).hexdigest(),
            "latest_run_status": status,
            "latest_run_started_at": started.isoformat() if started else None,
            "latest_run_finished_at": finished.isoformat() if finished else None,
            "last_success_at": success.isoformat() if success else None,
            "checkpoint_updated_at": checkpoint_at.isoformat() if checkpoint_at else None,
            "checkpoint_relation": relation,
            "running_age_minutes": age,
            "observation_versions": _count(row["observation_versions"]),
            "provider_keys": _count(row["provider_keys"]),
            "attention_reasons": reasons,
        })
    truncated = summary["lanes_truncated"]
    unrepresented_running = max(0, counts["running_runs"] - sum(
        lane["latest_run_status"] == "RUNNING" for lane in lanes
    ))
    global_reasons = ["RUNNING_ROWS_NOT_REPRESENTED_AS_LATEST"] if unrepresented_running else []
    attention |= bool(global_reasons)
    return {
        "status": "ATTENTION" if attention else "PARTIAL" if truncated else
                  "NO_RUNS" if counts["runs"] == 0 else "OBSERVED",
        "checked_at_utc": observed.isoformat(),
        "counts": counts,
        "lanes": lanes,
        "lanes_truncated": truncated,
        "unrepresented_running_run_rows": unrepresented_running,
        "attention_reasons": global_reasons,
        "running_age_threshold_minutes": running_age_minutes,
        "write_performed": False,
        "source_fetch_performed": False,
        "sole_writer_exclusion_proven": False,
        "source_coverage": "NOT_ASSESSED",
        "parser_content_verification": "NOT_RUN_BY_THIS_COMMAND",
        "database_physical_integrity": "NOT_RUN_BY_THIS_COMMAND",
        "semantics": "STORED_STATE_NOT_SOURCE_FRESHNESS_IDENTITY_OR_PUBLICATION_APPROVAL",
    }
