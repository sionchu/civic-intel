from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import pytest

from workers import scheduled_acquisition as sa

TODAY = date(2026, 10, 4)
KEYS = {
    "ASSEMBLY_API_KEY": "assembly-secret-123",
    "DART_API_KEY": "dart-secret-1234567",
    "MOIS_ORG_CODE_API_KEY": "mois-secret-123",
    "CIVIC_DART_BUSINESS_YEAR": "2025",
    "CIVIC_DART_REPORT_CODE": "11011",
    "CIVIC_ASSEMBLY_FROM_YEAR": "2024",
}


def fake_runner(stdout: str = '{"status": "SUCCESS", "run_id": "r1"}', code: int = 0, stderr: str = ""):
    calls: list[list[str]] = []

    def run(command, **kwargs):
        calls.append(command)
        assert "env" in kwargs and kwargs["capture_output"] is True
        return subprocess.CompletedProcess(command, code, stdout=stdout, stderr=stderr)

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_jobs_never_pass_materialization_or_publication_flags() -> None:
    for job in sa.JOBS:
        args = job.argv(KEYS, TODAY)
        assert not sa.FORBIDDEN_FLAGS.intersection(args), job.name
        assert job.cadence in sa.CADENCES
    assert "workers.sync" not in {job.module for job in sa.JOBS}  # civic-sync also materializes


def test_forbidden_flag_is_rejected() -> None:
    job = sa.AcquisitionJob("bad", "daily", "workers.assembly_roster", sa._fixed("--enumerate", "--materialize"))
    with pytest.raises(sa.AcquisitionConfigError):
        job.argv({}, TODAY)


def test_missing_credential_blocks_without_running() -> None:
    runner = fake_runner()
    job = next(item for item in sa.JOBS if item.name == "assembly-roster")
    receipt = sa.run_job(job, {}, TODAY, runner=runner)
    assert receipt.status == "BLOCKED_CREDENTIAL"
    assert runner.calls == []  # type: ignore[attr-defined]


def test_dart_period_must_be_explicit() -> None:
    job = next(item for item in sa.JOBS if item.name == "opendart-listed-executives")
    receipt = sa.run_job(job, {"DART_API_KEY": "x" * 40}, TODAY, runner=fake_runner())
    assert receipt.status == "BLOCKED_CONFIG"
    assert job.argv(KEYS, TODAY)[-4:] == ("--business-year", "2025", "--report-code", "11011")


def test_gwanbo_is_not_scheduled_while_it_returns_zero_notices() -> None:
    assert "gwanbo-personnel" not in {job.name for job in sa.JOBS}


def test_success_failure_and_partial_mapping_with_redaction() -> None:
    job = next(item for item in sa.JOBS if item.name == "assembly-bills")
    ok = sa.run_job(job, KEYS, TODAY, runner=fake_runner())
    assert ok.status == "SUCCESS" and ok.worker_receipt == {"status": "SUCCESS", "run_id": "r1"}
    partial = sa.run_job(job, KEYS, TODAY, runner=fake_runner('{"status": "PARTIAL"}'))
    assert partial.status == "WORKER_PARTIAL"
    failed = sa.run_job(job, KEYS, TODAY,
                        runner=fake_runner("", 2, "boom assembly-secret-123 tail"))
    assert failed.status == "FAILED"
    assert "assembly-secret-123" not in json.dumps(failed.to_dict())
    assert "<ASSEMBLY_API_KEY>" in (failed.detail or "")


def test_main_writes_receipt_outside_repo_and_uses_exit_codes(tmp_path: Path, monkeypatch) -> None:
    env = {"CIVIC_ACQUISITION_RECEIPTS_DIR": str(tmp_path)}
    monkeypatch.setattr(sa.subprocess, "run", fake_runner('{"status": "SUCCESS"}'))
    # weekly: ALIO (no key) succeeds; keyed jobs have no key -> blocked -> exit 3
    assert sa.main(["--cadence", "weekly"], env=env, today=TODAY) == 3
    lines = (tmp_path / "2026-10.jsonl").read_text(encoding="utf-8").splitlines()
    statuses = {item["job"]: item["status"] for item in json.loads(lines[-1])["jobs"]}
    assert statuses == {
        "assembly-votes": "BLOCKED_CREDENTIAL",
        "assembly-meeting-graph": "BLOCKED_CREDENTIAL",
        "alio-executives": "SUCCESS",
        "mois-organization-codes": "BLOCKED_CREDENTIAL",
    }
    assert not (tmp_path / "acquisition.lock").exists()


def test_lock_prevents_overlapping_runs(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "acquisition.lock").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sa.subprocess, "run", fake_runner())
    env = {"CIVIC_ACQUISITION_RECEIPTS_DIR": str(tmp_path)}
    assert sa.main(["--cadence", "daily"], env=env, today=TODAY) == 75
    assert sa.main(["--cadence", "daily", "--dry-run"], env=env | KEYS, today=TODAY) == 0


def test_resume_requires_one_job() -> None:
    with pytest.raises(SystemExit):
        sa.main(["--cadence", "daily", "--resume"], env={}, today=TODAY)


def test_assembly_meeting_jobs_require_explicit_from_year():
    job = next(item for item in sa.JOBS if item.name == "assembly-meeting-graph")
    with pytest.raises(sa.AcquisitionConfigError, match="CIVIC_ASSEMBLY_FROM_YEAR"):
        job.argv({"CIVIC_ASSEMBLY_AGE": "22"}, date(2026, 10, 5))
    env = {"CIVIC_ASSEMBLY_AGE": "22", "CIVIC_ASSEMBLY_FROM_YEAR": "2024"}
    assert job.argv(env, date(2026, 10, 5)) == (
        "--age", "22", "--from-year", "2024", "--enumerate",
    )
    universe = next(item for item in sa.JOBS if item.name == "assembly-meeting-universe")
    assert universe.cadence == "daily"
    assert universe.argv(env, date(2026, 10, 5)) == ("--age", "22", "--from-year", "2024")


def test_assembly_votes_job_enumerates_the_configured_term():
    job = next(item for item in sa.JOBS if item.name == "assembly-votes")
    assert job.cadence == "weekly"
    assert job.module == "workers.assembly_roll_call_votes"
    assert job.argv({"CIVIC_ASSEMBLY_AGE": "22"}, date(2026, 10, 5)) == ("--age", "22", "--enumerate")
    assert job.required_env == ("ASSEMBLY_API_KEY",)
