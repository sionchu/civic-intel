"""Scheduled acquisition runner for already-approved L3 source lanes.

This is a thin, explicit job list over existing source-specific workers. It runs each worker in a
child process with acquisition-only flags (observations, runs and checkpoints). It never passes
materialization, publication, review-resolution or Claim-commit flags, so a scheduled run cannot
create People, publish Claims or change public output. Those remain separate reviewed operations.

Receipts are written outside the repository and the canonical database (one JSON line per job).
Credentials are read from the process environment by the workers themselves and are never placed
in argv, receipts or logs.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Self

CADENCES = ("daily", "weekly", "monthly")
CREDENTIAL_ENV = (
    "ASSEMBLY_API_KEY",
    "DART_API_KEY",
    "MOIS_ORG_CODE_API_KEY",
    "NEC_API_KEY",
    "NKIS_API_KEY",
)
FORBIDDEN_FLAGS = frozenset(
    {
        "--materialize",
        "--publish-base-profile",
        "--publish-claims",
        "--resolve-review-item",
        "--commit",
    }
)
DEFAULT_TIMEOUT_SECONDS = 4 * 60 * 60
STDERR_TAIL_CHARS = 1500


class AcquisitionConfigError(ValueError):
    """A job needs an explicit operator setting that is absent or invalid."""


@dataclass(frozen=True)
class AcquisitionJob:
    name: str
    cadence: str
    module: str
    build_args: Callable[[Mapping[str, str], date], tuple[str, ...]]
    required_env: tuple[str, ...] = ()
    note: str = ""
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    def argv(self, env: Mapping[str, str], today: date) -> tuple[str, ...]:
        args = self.build_args(env, today)
        forbidden = FORBIDDEN_FLAGS.intersection(args)
        if forbidden:
            raise AcquisitionConfigError(f"{self.name} would pass forbidden flags {sorted(forbidden)}")
        return args


def _fixed(*args: str) -> Callable[[Mapping[str, str], date], tuple[str, ...]]:
    return lambda _env, _today: args


def _assembly_bills(env: Mapping[str, str], _today: date) -> tuple[str, ...]:
    age = env.get("CIVIC_ASSEMBLY_AGE", "22").strip()
    if not age.isdigit():
        raise AcquisitionConfigError("CIVIC_ASSEMBLY_AGE must be an Assembly term number")
    return ("--age", age, "--enumerate-bills")


def _dart_period(env: Mapping[str, str], _today: date) -> tuple[str, ...]:
    year = env.get("CIVIC_DART_BUSINESS_YEAR", "").strip()
    report = env.get("CIVIC_DART_REPORT_CODE", "").strip()
    if not (year.isdigit() and len(year) == 4) or report not in {"11011", "11012", "11013", "11014"}:
        raise AcquisitionConfigError(
            "CIVIC_DART_BUSINESS_YEAR (YYYY) and CIVIC_DART_REPORT_CODE "
            "(11011/11012/11013/11014) must name the report period explicitly"
        )
    return (
        "--dataset", "EXECUTIVE_STATUS", "--enumerate", "--listed-only",
        "--business-year", year, "--report-code", report,
    )


JOBS: tuple[AcquisitionJob, ...] = (
    AcquisitionJob(
        "assembly-roster", "daily", "workers.assembly_roster", _fixed("--enumerate"),
        ("ASSEMBLY_API_KEY",), "current roster observations; no --materialize",
    ),
    AcquisitionJob(
        "assembly-bills", "daily", "workers.legislative_activity", _assembly_bills,
        ("ASSEMBLY_API_KEY",), "bill participation observations; no --publish-claims",
    ),
    AcquisitionJob(
        "alio-executives", "weekly", "workers.public_institutions", _fixed(),
        (), "ALIO item 4 current executive disclosures",
    ),
    AcquisitionJob(
        "mois-organization-codes", "weekly", "workers.mois_organization_codes", _fixed(),
        ("MOIS_ORG_CODE_API_KEY",), "current standard organization-code universe",
    ),
    AcquisitionJob(
        "opendart-listed-executives", "monthly", "workers.corporate_talent", _dart_period,
        ("DART_API_KEY",), "listed-corporation executive status for one explicit report period",
    ),
)


@dataclass
class JobReceipt:
    job: str
    cadence: str
    status: str
    started_at: str
    finished_at: str
    exit_code: int | None = None
    worker_receipt: dict[str, Any] | None = None
    detail: str | None = None
    argv: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value not in (None, [])}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def redact(text: str, env: Mapping[str, str]) -> str:
    for name in CREDENTIAL_ENV:
        secret = env.get(name)
        if secret and len(secret) >= 6:
            text = text.replace(secret, f"<{name}>")
    database_url = env.get("DATABASE_URL", "")
    if "@" in database_url:
        text = text.replace(database_url, "<DATABASE_URL>")
    return text


def _worker_json(stdout: str) -> dict[str, Any] | None:
    start = stdout.find("{")
    while start != -1:
        try:
            value = json.loads(stdout[start:])
        except json.JSONDecodeError:
            start = stdout.find("{", start + 1)
            continue
        return value if isinstance(value, dict) else None
    return None


def run_job(
    job: AcquisitionJob,
    env: Mapping[str, str],
    today: date,
    *,
    resume: bool = False,
    dry_run: bool = False,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> JobReceipt:
    started = _now()
    missing = [name for name in job.required_env if not env.get(name, "").strip()]
    if missing:
        return JobReceipt(job.name, job.cadence, "BLOCKED_CREDENTIAL", started, _now(),
                          detail=f"missing environment variable(s): {', '.join(missing)}")
    try:
        args = list(job.argv(env, today))
    except AcquisitionConfigError as exc:
        return JobReceipt(job.name, job.cadence, "BLOCKED_CONFIG", started, _now(), detail=str(exc))
    if resume:
        args.append("--resume")
    if dry_run:
        return JobReceipt(job.name, job.cadence, "PLANNED", started, _now(), argv=args)
    command = [sys.executable, "-m", job.module, *args]
    try:
        completed = (runner or subprocess.run)(command, env=dict(env), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=job.timeout_seconds)
    except subprocess.TimeoutExpired:
        return JobReceipt(job.name, job.cadence, "TIMEOUT", started, _now(), argv=args,
                          detail=f"exceeded {job.timeout_seconds}s; rerun with --only {job.name} --resume")
    worker_receipt = _worker_json(redact(completed.stdout or "", env))
    reported = str((worker_receipt or {}).get("status", "")).upper()
    if completed.returncode != 0:
        status = "FAILED"
    elif worker_receipt is None:
        status = "SUCCESS_NO_RECEIPT"
    elif reported == "SUCCESS":
        status = "SUCCESS"
    else:
        status = f"WORKER_{reported or 'UNKNOWN'}"
    detail = None
    if status != "SUCCESS":
        detail = redact(completed.stderr or "", env)[-STDERR_TAIL_CHARS:].strip() or None
    return JobReceipt(job.name, job.cadence, status, started, _now(),
                      exit_code=completed.returncode, worker_receipt=worker_receipt,
                      detail=detail, argv=args)


def select_jobs(cadence: str | None, only: Sequence[str]) -> list[AcquisitionJob]:
    names = {job.name for job in JOBS}
    unknown = sorted(set(only) - names)
    if unknown:
        raise AcquisitionConfigError(f"unknown job(s): {', '.join(unknown)}")
    if only:
        return [job for job in JOBS if job.name in only]
    if cadence is None:
        raise AcquisitionConfigError("choose --cadence or --only")
    return [job for job in JOBS if job.cadence == cadence]


def receipts_dir(env: Mapping[str, str]) -> Path:
    configured = env.get("CIVIC_ACQUISITION_RECEIPTS_DIR", "").strip()
    return Path(configured) if configured else Path.home() / ".civic-intel" / "acquisition-receipts"


class RunLock:
    """Exclusive lock file so overlapping schedules never run two collectors at once."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def __enter__(self) -> Self:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return self
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps({"pid": os.getpid(), "started_at": _now()}))
        self.acquired = True
        return self

    def __exit__(self, *_exc: object) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run scheduled acquisition-only jobs over approved L3 source lanes."
    )
    parser.add_argument("--cadence", choices=CADENCES)
    parser.add_argument("--only", action="append", default=[], metavar="JOB")
    parser.add_argument("--resume", action="store_true",
                        help="resume an interrupted run; only valid with exactly one --only job")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without fetching")
    parser.add_argument("--list", action="store_true", help="list jobs and exit")
    return parser


def main(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None,
         today: date | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    environment = dict(os.environ if env is None else env)
    if args.list:
        for job in JOBS:
            print(f"{job.name}\t{job.cadence}\t{','.join(job.required_env) or '-'}\t{job.note}")
        return 0
    if args.resume and len(args.only) != 1:
        parser.error("--resume requires exactly one --only job")
    try:
        jobs = select_jobs(args.cadence, args.only)
    except AcquisitionConfigError as exc:
        parser.error(str(exc))
    run_day = today or datetime.now(UTC).astimezone().date()
    directory = receipts_dir(environment)
    label = args.cadence or "manual"
    with RunLock(directory / "acquisition.lock") as lock:
        if not lock.acquired and not args.dry_run:
            print(json.dumps({"status": "SKIPPED_LOCKED", "cadence": label}, ensure_ascii=False))
            return 75
        receipts = [run_job(job, environment, run_day, resume=args.resume, dry_run=args.dry_run)
                    for job in jobs]
    summary = {
        "cadence": label,
        "run_day": run_day.isoformat(),
        "dry_run": args.dry_run,
        "jobs": [receipt.to_dict() for receipt in receipts],
    }
    if not args.dry_run:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / f"{run_day:%Y-%m}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    statuses = {receipt.status for receipt in receipts}
    if statuses & {"FAILED", "TIMEOUT"} or any(item.startswith("WORKER_") for item in statuses):
        return 1
    if statuses & {"BLOCKED_CREDENTIAL", "BLOCKED_CONFIG"}:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
