from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import event, text

from apps.cli.main import main
from packages.application.context import Application
from packages.application.errors import ConcurrentWrite
from packages.persistence.database import Database
from packages.rendering.collection_status import build_collection_status
from tests.test_batch_mois_organization_codes import (
    MoisApi,
    migrated_repository,
    organization_row,
)
from workers.mois_organization_codes import MoisOrganizationEnumerator


def captured_repository(tmp_path: Path):
    repo = migrated_repository(tmp_path / "monitor.db")
    api = MoisApi({1: [organization_row("A123456", "合成検証機関")]})
    worker = MoisOrganizationEnumerator(api.connector(), repo)
    worker.enumerate()
    return repo, api, worker


def test_empty_migrated_database_is_no_runs_and_not_a_coverage_pass(tmp_path):
    repo = migrated_repository(tmp_path / "empty.db")
    report = build_collection_status(repo.operator_summary(monitoring=True))
    assert report["status"] == "NO_RUNS" and report["counts"]["runs"] == 0
    assert report["source_coverage"] == "NOT_ASSESSED"
    assert report["database_physical_integrity"] == "NOT_RUN_BY_THIS_COMMAND"
    assert not report["sole_writer_exclusion_proven"]


def test_latest_failed_attempt_keeps_previous_success_and_checkpoint_separate(tmp_path):
    repo, api, worker = captured_repository(tmp_path)
    api.fail_pages.add(1)
    with pytest.raises(RuntimeError):
        worker.enumerate()
    report = build_collection_status(repo.operator_summary(monitoring=True))
    lane = report["lanes"][0]
    assert report["status"] == "ATTENTION"
    assert lane["latest_run_status"] == "FAILED"
    assert lane["last_success_at"] is not None
    assert lane["checkpoint_relation"] == "PRIOR_RUN"
    assert "CHECKPOINT_REFERENCE_INVALID" not in lane["attention_reasons"]
    assert "CHECKPOINT_CURSOR_MISMATCH" not in lane["attention_reasons"]
    assert report["counts"]["observations"] == 1


def test_monitor_redacts_scope_and_stored_payload_and_preserves_version_counts(tmp_path):
    repo, _, worker = captured_repository(tmp_path)
    worker.enumerate()
    with repo.engine.begin() as c:
        c.execute(text("UPDATE source_runs SET metadata_json=:payload, error_summary=:secret"),
                  {"payload": '{"token":"NEVER_LEAK"}', "secret": "NEVER_LEAK"})
        c.execute(text("UPDATE source_runs SET scope_key=:secret"), {"secret": "NEVER_LEAK"})
        c.execute(text("UPDATE source_checkpoints SET scope_key=:secret"), {"secret": "NEVER_LEAK"})
        c.execute(text("UPDATE feeder_observations SET scope_key=:secret"), {"secret": "NEVER_LEAK"})
    report = build_collection_status(repo.operator_summary(monitoring=True))
    encoded = json.dumps(report)
    assert "NEVER_LEAK" not in encoded and "A123456" not in encoded
    assert "mois_standard_organization_codes" not in encoded
    assert len(report["lanes"][0]["lane_sha256"]) == 64
    assert report["counts"]["runs"] == 2 and report["counts"]["observations"] == 1
    assert report["lanes"][0]["checkpoint_relation"] == "LATEST_RUN"
    assert report["status"] == "OBSERVED"


@pytest.mark.parametrize("corruption,reason", [
    ("UPDATE source_checkpoints SET last_run_id=NULL", "CHECKPOINT_LINEAGE_UNAVAILABLE"),
    ("UPDATE source_runs SET scope_key='wrong-scope'", "CHECKPOINT_REFERENCE_INVALID"),
    ("UPDATE source_checkpoints SET cursor='secret-cursor'", "CHECKPOINT_CURSOR_MISMATCH"),
])
def test_lineage_anomalies_are_aggregate_only(tmp_path, corruption, reason):
    repo, _, _ = captured_repository(tmp_path)
    with repo.engine.begin() as c:
        c.execute(text(corruption))
    report = build_collection_status(repo.operator_summary(monitoring=True))
    assert report["status"] == "ATTENTION"
    assert any(reason in lane["attention_reasons"] for lane in report["lanes"])
    assert "secret-cursor" not in json.dumps(report)


@pytest.mark.parametrize("age,reason", [(61, "RUN_AGE_THRESHOLD_EXCEEDED"),
                                       (-1, "RUN_START_IN_FUTURE")])
def test_running_age_is_a_review_threshold_not_a_process_kill(tmp_path, age, reason):
    repo = migrated_repository(tmp_path / "running.db")
    run = repo.start_source_run("fixture", "scope")
    now = datetime.now(UTC)
    with repo.engine.begin() as c:
        c.execute(text("UPDATE source_runs SET started_at=:started"),
                  {"started": (now - timedelta(minutes=age)).isoformat()})
    report = build_collection_status(repo.operator_summary(monitoring=True), now=now)
    assert report["counts"]["running_runs"] == 1
    assert report["status"] == "ATTENTION"
    assert reason in report["lanes"][0]["attention_reasons"]
    assert repo.source_run(run.id).status.value == "RUNNING"


def test_truncated_scope_checks_are_partial_not_verified_all(tmp_path):
    repo = migrated_repository(tmp_path / "truncated.db")
    summary = repo.operator_summary(monitoring=True)
    summary["lanes_truncated"] = True
    assert build_collection_status(summary)["status"] == "PARTIAL"


def test_summary_remains_two_selects_and_one_read_snapshot(tmp_path):
    repo, _, _ = captured_repository(tmp_path)
    statements = []
    event.listen(repo.engine, "before_cursor_execute", lambda *args: statements.append(args[2]))
    build_collection_status(repo.operator_summary(monitoring=True))
    assert sum(q.lstrip().upper().startswith("SELECT") for q in statements) == 2
    assert sum(q.lstrip().upper().startswith("BEGIN") for q in statements) == 1


def test_default_operator_surface_does_not_gain_monitor_fields(tmp_path):
    repo, _, _ = captured_repository(tmp_path)
    summary = repo.operator_summary()
    assert "running_runs" not in summary["counts"]
    assert "checkpoint_run_id" not in summary["lanes"][0]


def test_older_running_attempt_is_not_hidden_by_later_success(tmp_path):
    repo, _, _ = captured_repository(tmp_path)
    older = repo.start_source_run(MoisOrganizationEnumerator.FEEDER,
                                  MoisOrganizationEnumerator.SCOPE_KEY)
    with repo.engine.begin() as c:
        c.execute(text("UPDATE source_runs SET started_at=:started WHERE id=:id"),
                  {"started": datetime(2000, 1, 1, tzinfo=UTC).isoformat(), "id": str(older.id)})
    report = build_collection_status(repo.operator_summary(monitoring=True))
    assert report["lanes"][0]["latest_run_status"] == "SUCCESS"
    assert report["unrepresented_running_run_rows"] == 1
    assert report["attention_reasons"] == ["RUNNING_ROWS_NOT_REPRESENTED_AS_LATEST"]
    assert report["status"] == "ATTENTION"


def test_multiple_running_rows_on_one_visible_lane_are_counted_as_rows(tmp_path):
    repo = migrated_repository(tmp_path / "concurrent.db")
    repo.start_source_run("fixture", "same-lane")
    repo.start_source_run("fixture", "same-lane")
    report = build_collection_status(repo.operator_summary(monitoring=True))
    assert len(report["lanes"]) == 1
    assert report["lanes"][0]["latest_run_status"] == "RUNNING"
    assert report["counts"]["running_runs"] == 2
    assert report["unrepresented_running_run_rows"] == 1
    assert report["status"] == "ATTENTION"


def test_null_cursor_is_unavailable_not_a_mismatch(tmp_path):
    repo, _, _ = captured_repository(tmp_path)
    with repo.engine.begin() as c:
        c.execute(text("UPDATE source_checkpoints SET cursor=NULL"))
    report = build_collection_status(repo.operator_summary(monitoring=True))
    assert "CHECKPOINT_CURSOR_COMPARISON_UNAVAILABLE" in report["lanes"][0]["attention_reasons"]
    assert "CHECKPOINT_CURSOR_MISMATCH" not in report["lanes"][0]["attention_reasons"]


def test_cli_sqlite_monitor_uses_existing_file_read_only_and_does_not_write(tmp_path, capsys):
    path = tmp_path / "cli.db"
    repo = migrated_repository(path)
    repo.close()
    before = path.read_bytes()
    assert main(["inspect", "collection-status", "--database-url", f"sqlite:///{path.as_posix()}"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["effect"] == "READ_ONLY"
    assert output["result"]["status"] == "NO_RUNS"
    assert output["result"]["schema_revision"] == "0008"
    assert path.read_bytes() == before
    from apps.cli.adapters import _read_only_monitor_url

    read_db = Database(_read_only_monitor_url(f"sqlite:///{path.as_posix()}"))
    with pytest.raises(ConcurrentWrite):
        Application(read_db).acquisition.start_source_run("fixture", "write-canary")
    assert Application(read_db).acquisition.source_runs() == []
    read_db.close()


def test_missing_database_is_unavailable_without_creating_a_file(tmp_path, capsys):
    path = tmp_path / "missing.db"
    with pytest.raises(SystemExit) as stopped:
        main(["inspect", "collection-status", "--database-url", f"sqlite:///{path.as_posix()}"])
    assert stopped.value.code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "UNAVAILABLE"
    assert "counts" not in output and not path.exists()


def test_connection_error_is_unavailable_without_error_text_or_zero_counts(monkeypatch, capsys):
    from apps.cli import adapters

    def fail(_):
        raise RuntimeError("NEVER_LEAK_CONNECTION_SECRET")

    monkeypatch.setattr(adapters, "dispatch", fail)
    assert main(["inspect", "collection-status", "--database-url", "sqlite:///unused.db"]) == 1
    output = capsys.readouterr().out
    assert "NEVER_LEAK" not in output
    assert json.loads(output)["status"] == "UNAVAILABLE" and "counts" not in json.loads(output)


@pytest.mark.parametrize("revision", ["0006", "0007"])
def test_reader_compatible_revisions_are_observed_without_migration(tmp_path, capsys, revision):
    from alembic import command
    from alembic.config import Config

    path = tmp_path / "compatible.db"
    url = f"sqlite:///{path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, revision)
    before = path.read_bytes()
    assert main(["inspect", "collection-status", "--database-url", url]) == 0
    assert json.loads(capsys.readouterr().out)["result"]["schema_revision"] == revision
    assert path.read_bytes() == before


@pytest.mark.parametrize("flags", [[], ["--running-age-minutes", "0"],
                                 ["--running-age-minutes", "10081"], ["--resume"],
                                 ["--allow-effect", "SOURCE_INGESTION"]])
def test_cli_monitor_invalid_arguments_precede_database_dispatch(monkeypatch, flags):
    from apps.cli import adapters

    def forbidden(_):
        pytest.fail("invalid monitor scope was dispatched")

    monkeypatch.setattr(adapters, "dispatch", forbidden)
    argv = ["inspect", "collection-status"]
    if flags:
        argv += ["--database-url", "sqlite:///unused.db", *flags]
    with pytest.raises(SystemExit) as stopped:
        main(argv)
    assert stopped.value.code == 2
