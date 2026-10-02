from __future__ import annotations

import contextlib
import hashlib
import json
import os
import stat
import subprocess
import types
import zipfile

import pytest
from alembic import command
from alembic.config import Config

from scripts import mac_assembly_one_shot as launcher
from tests.test_batch_assembly import migrated_repository, three_member_api
from workers.assembly_roster import AssemblyRosterEnumerator

DUMMY = "fixture-key-do-not-print"
DUMMY_BYTES = DUMMY.encode()
OUTCOME = {"exit_code": 0, "forced_stop": False, "process_reaped": True}


def request_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    request = {
        "live_run_authorized": True,
        "target": launcher.TARGET_ALIAS,
        "source_policy": {
            "id": "11000000-0000-0000-0000-000000000001",
            "terms_checked_at": "2026-08-30T00:00:00Z",
        },
    }
    raw = json.dumps(request).encode()
    path = tmp_path / "requests/assembly-one-shot.json"
    path.parent.mkdir()
    path.write_bytes(raw)
    monkeypatch.setattr(launcher, "REQUEST_SHA256", hashlib.sha256(raw).hexdigest())
    return path, request


def test_request_pin_rejects_even_one_changed_byte(tmp_path, monkeypatch) -> None:
    path, request = request_fixture(tmp_path, monkeypatch)
    assert launcher._request() == request
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(launcher.PreflightError, match="REQUEST_DRIFT"):
        launcher._request()


def test_policy_terms_drift_is_rejected(tmp_path, monkeypatch) -> None:
    _, request = request_fixture(tmp_path, monkeypatch)
    assert str(launcher._policy(request).id) == request["source_policy"]["id"]
    request["source_policy"]["terms_checked_at"] = "2026-09-01T00:00:00Z"
    with pytest.raises(launcher.PreflightError, match="POLICY_DRIFT"):
        launcher._policy(request)


@pytest.mark.parametrize(
    ("mode", "uid", "links", "directory"),
    [(0o644, 10, 1, False), (0o600, 11, 1, False), (0o600, 10, 2, False), (0o600, 10, 1, True)],
)
def test_owned_file_check_rejects_unsafe_metadata(monkeypatch, mode, uid, links, directory):
    monkeypatch.setattr(os, "getuid", lambda: 10, raising=False)
    info = types.SimpleNamespace(
        st_mode=(stat.S_IFDIR if directory else stat.S_IFREG) | mode,
        st_uid=uid,
        st_nlink=links,
    )
    with pytest.raises(launcher.PreflightError, match="UNSAFE_FILE"):
        launcher._owned(info, 0o600)


def key_fixture(monkeypatch, *, value=DUMMY_BYTES, missing=False, mode=0o600):
    monkeypatch.setattr(launcher, "_no_symlinks", lambda _path: None)
    monkeypatch.setattr(os, "getuid", lambda: 10, raising=False)
    monkeypatch.setattr(os, "O_DIRECTORY", 0, raising=False)
    monkeypatch.setattr(os, "O_NOFOLLOW", 0, raising=False)

    def opening(path, _flags, **kwargs):
        if str(path) == "assembly-api-key.txt":
            assert kwargs == {"dir_fd": 11}
            if missing:
                raise FileNotFoundError(DUMMY)
            return 12
        return 11

    monkeypatch.setattr(os, "open", opening)
    monkeypatch.setattr(os, "close", lambda _fd: None)
    monkeypatch.setattr(os, "read", lambda _fd, _size: value)
    monkeypatch.setattr(
        os,
        "fstat",
        lambda fd: types.SimpleNamespace(
            st_mode=(stat.S_IFDIR | 0o700) if fd == 11 else (stat.S_IFREG | mode),
            st_uid=10,
            st_nlink=1,
            st_size=len(value),
        ),
    )


@pytest.mark.parametrize("value", [b"", b"abc\x00def", b"ab cd", b"\xff", b"x" * 1025])
def test_key_reader_rejects_bad_fixture_without_echo(monkeypatch, value):
    key_fixture(monkeypatch, value=value)
    with pytest.raises(launcher.PreflightError) as failure:
        launcher._read_key()
    assert str(failure.value) == "UNSAFE_CREDENTIAL"


def test_key_reader_checks_private_slot_and_handles_missing(monkeypatch):
    key_fixture(monkeypatch)
    assert launcher._read_key() == DUMMY
    key_fixture(monkeypatch, mode=0o644)
    with pytest.raises(launcher.PreflightError, match="UNSAFE_CREDENTIAL"):
        launcher._read_key()
    key_fixture(monkeypatch, missing=True)
    with pytest.raises(launcher.PreflightError, match="CREDENTIAL_MISSING") as failure:
        launcher._read_key()
    assert DUMMY not in str(failure.value)


def test_child_environment_is_explicit_and_command_keeps_fixed_scope(monkeypatch):
    monkeypatch.setenv("DEPLOY_TOKEN", DUMMY)
    monkeypatch.setenv("SSL_CERT_FILE", "/fixture-ca")
    monkeypatch.setenv("DATABASE_URL", DUMMY)
    env = launcher._child_environment(DUMMY, "http://127.0.0.1:1234")
    assert set(env) == {
        "HOME",
        "PATH",
        "TMPDIR",
        "PYTHONDONTWRITEBYTECODE",
        "ASSEMBLY_API_KEY",
        "HTTPS_PROXY",
    }
    assert env["ASSEMBLY_API_KEY"] == DUMMY
    argv = launcher._command(1234)
    assert "observe" in argv and "assembly" in argv
    assert "--resume" not in argv and "--name" not in argv
    assert DUMMY not in repr(argv)
    profile = launcher._sandbox(1234)
    assert "(deny default)" in profile
    assert '(remote ip "localhost:1234")' in profile
    assert "credentials" not in profile and "/release" not in profile
    for suffix in ("", "-journal", "-wal", "-shm"):
        assert json.dumps(str(launcher.TARGET) + suffix) in profile


class FakeProcess:
    def __init__(self, timeouts=0):
        self.pid = 42
        self.returncode = None
        self.timeouts = timeouts
        self.waits = []

    def communicate(self, *, timeout):
        self.waits.append(timeout)
        if self.timeouts:
            self.timeouts -= 1
            raise subprocess.TimeoutExpired(DUMMY, timeout, output=DUMMY)
        self.returncode = 0 if len(self.waits) == 1 else -9
        return DUMMY.encode(), DUMMY.encode()


def test_watchdog_escalates_term_kill_reaps_and_discards_output(monkeypatch):
    killed = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: killed.append((pid, sig)), raising=False)
    monkeypatch.setattr(launcher.signal, "SIGKILL", 9, raising=False)
    process = FakeProcess(timeouts=2)
    result = launcher._watch(process)
    assert process.waits == [180, 5, 5]
    assert killed == [(42, launcher.signal.SIGTERM), (42, 9)]
    assert result == {"exit_code": -9, "forced_stop": True, "process_reaped": True}
    assert DUMMY not in repr(result)


def test_watchdog_reports_unreaped_process(monkeypatch):
    monkeypatch.setattr(os, "killpg", lambda *_args: None, raising=False)
    monkeypatch.setattr(launcher.signal, "SIGKILL", 9, raising=False)
    assert launcher._watch(FakeProcess(timeouts=3)) == {
        "exit_code": None,
        "forced_stop": True,
        "process_reaped": False,
    }


def test_canonical_receipt_reads_actual_fixture_run_and_checkpoint(tmp_path):
    repository = migrated_repository(tmp_path / "success.sqlite")
    result = AssemblyRosterEnumerator(
        three_member_api().connector(), repository.application
    ).enumerate()
    receipt = launcher._canonical_receipt(repository, OUTCOME)
    assert receipt["status"] == "SUCCESS"
    assert receipt["canonical"]["source_run_id"] == str(result.run.id)
    assert receipt["canonical"]["status"] == "SUCCESS"
    assert receipt["canonical"]["checkpoint"] == "2"
    assert receipt["canonical"]["observation_count"] == 3
    with pytest.raises(launcher.PreflightError, match="TARGET_NOT_EMPTY"):
        launcher._pristine(repository)
    stopped = launcher._canonical_receipt(repository, OUTCOME | {"forced_stop": True})
    assert stopped["status"] == "RECOVERY_REQUIRED"
    assert stopped["canonical"] == receipt["canonical"]


def test_running_receipt_requires_recovery_and_never_rewrites_run(tmp_path):
    repository = migrated_repository(tmp_path / "running.sqlite")
    run = repository.start_source_run(launcher.FEEDER, launcher.SCOPE)
    receipt = launcher._canonical_receipt(repository, OUTCOME)
    assert receipt["status"] == "RECOVERY_REQUIRED"
    assert receipt["canonical"]["status"] == "RUNNING"
    assert receipt["canonical"]["checkpoint"] is None
    assert repository.source_run(run.id).status.value == "RUNNING"


def test_old_schema_fails_without_migrating(tmp_path, monkeypatch):
    path = tmp_path / "old.sqlite"
    repository = migrated_repository(path)
    repository.close()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///" + path.as_posix())
    command.downgrade(config, "0007")
    monkeypatch.setattr(launcher, "TARGET", path)
    monkeypatch.setattr(launcher, "_owned", lambda *_a, **_k: None)
    with pytest.raises(launcher.PreflightError, match="SCHEMA_MISMATCH"):
        launcher._database()
    from packages.persistence.database import Database

    database = Database("sqlite:///" + path.as_posix())
    assert database.schema_revision() == "0007"
    database.close()


def test_missing_key_blocks_before_listener_process_or_source_run(tmp_path, monkeypatch):
    request_fixture(tmp_path, monkeypatch)
    repository = migrated_repository(tmp_path / "empty.sqlite")
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "_verify_runtime", lambda: None)
    monkeypatch.setattr(launcher, "_owned_lock", contextlib.nullcontext)
    monkeypatch.setattr(launcher, "_database", lambda: repository)
    monkeypatch.setattr(launcher, "_relay", lambda _policy: pytest.fail("relay started"))

    def missing():
        raise launcher.PreflightError("CREDENTIAL_MISSING")

    monkeypatch.setattr(launcher, "_read_key", missing)
    receipt = launcher.run_one_shot()
    assert receipt == {
        "status": "BLOCKED",
        "error_code": "CREDENTIAL_MISSING",
        "target": launcher.TARGET_ALIAS,
    }
    assert repository.source_runs() == []


def test_raw_preflight_errors_and_unknown_arguments_are_not_exposed(monkeypatch, capsys):
    monkeypatch.setattr(launcher.sys, "platform", "darwin")

    def fail():
        raise RuntimeError(f"/private/path?KEY={DUMMY}")

    monkeypatch.setattr(launcher, "_request", fail)
    assert launcher.main([]) == 1
    assert launcher.main([DUMMY]) == 1
    text = capsys.readouterr().out
    assert DUMMY not in text and "/private/path" not in text
    assert '"LAUNCHER_FAILED"' in text and '"UNEXPECTED_ARGUMENTS"' in text


def runtime_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(launcher, "ROOT", tmp_path)
    release = tmp_path / "release"
    release.mkdir()
    installed = tmp_path / "venv/lib/site-packages"
    (installed / "packages").mkdir(parents=True)
    (installed / "packages/example.py").write_bytes(b"value = 1\n")
    wheel = release / "civic_intel-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("packages/example.py", b"value = 1\n")
    wheel_hash = hashlib.sha256(wheel.read_bytes()).hexdigest()
    monkeypatch.setattr(launcher, "WHEEL_SHA256", wheel_hash)
    files = {wheel.name: wheel_hash}
    for index in range(12):
        name = f"payload-{index}"
        (release / name).write_bytes(b"fixture")
        files[name] = hashlib.sha256(b"fixture").hexdigest()
    manifest = {
        "code_commit": launcher.CODE_COMMIT,
        "wheel_sha256": wheel_hash,
        "file_sha256": files,
    }
    (release / "manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(
        launcher,
        "MANIFEST_SHA256",
        hashlib.sha256(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    )
    relay = tmp_path / "assembly-egress.py"
    relay.write_bytes(b"fixture-relay")
    monkeypatch.setattr(launcher, "RELAY_SHA256", hashlib.sha256(relay.read_bytes()).hexdigest())
    monkeypatch.setattr(
        launcher.importlib.metadata,
        "distribution",
        lambda _name: types.SimpleNamespace(locate_file=lambda name: installed / name),
    )
    monkeypatch.setattr(launcher.sys, "executable", str(tmp_path / "venv/bin/python"))
    return release, installed


def test_runtime_pins_payloads_and_installed_python(tmp_path, monkeypatch):
    release, installed = runtime_fixture(tmp_path, monkeypatch)
    launcher._verify_runtime()
    (installed / "packages/example.py").write_bytes(b"value = 2\n")
    with pytest.raises(launcher.PreflightError, match="INSTALLED_CODE_DRIFT"):
        launcher._verify_runtime()
    (installed / "packages/example.py").write_bytes(b"value = 1\n")
    (release / "payload-1").write_bytes(DUMMY.encode())
    with pytest.raises(launcher.PreflightError, match="RUNTIME_DRIFT"):
        launcher._verify_runtime()


def test_unexpected_installed_module_fails_closed(tmp_path, monkeypatch):
    _, installed = runtime_fixture(tmp_path, monkeypatch)
    (installed / "packages/extra.py").write_bytes(b"fixture")
    with pytest.raises(launcher.PreflightError, match="INSTALLED_CODE_DRIFT"):
        launcher._verify_runtime()


def test_self_consistent_manifest_and_payload_tampering_is_rejected(tmp_path, monkeypatch):
    release, _ = runtime_fixture(tmp_path, monkeypatch)
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    (release / "payload-1").write_bytes(b"changed")
    manifest["file_sha256"]["payload-1"] = hashlib.sha256(b"changed").hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(launcher.PreflightError, match="RUNTIME_DRIFT"):
        launcher._verify_runtime()


def test_launcher_lock_contention_fails_closed(tmp_path, monkeypatch):
    target = tmp_path / "target.sqlite"
    monkeypatch.setattr(launcher, "TARGET", target)
    monkeypatch.setattr(launcher, "_owned", lambda *_a, **_k: None)
    monkeypatch.setattr(os, "O_NOFOLLOW", 0, raising=False)

    def busy(*_args):
        raise BlockingIOError(DUMMY)

    monkeypatch.setitem(
        launcher.sys.modules,
        "fcntl",
        types.SimpleNamespace(
            flock=busy,
            LOCK_EX=1,
            LOCK_NB=2,
        ),
    )
    with pytest.raises(launcher.PreflightError, match="LAUNCHER_BUSY"), launcher._owned_lock():
        pytest.fail("contending launcher acquired lock")


def test_nonempty_target_blocks_before_credential_read(tmp_path, monkeypatch):
    request_fixture(tmp_path, monkeypatch)
    repository = migrated_repository(tmp_path / "notempty.sqlite")
    repository.start_source_run(launcher.FEEDER, launcher.SCOPE)
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "_verify_runtime", lambda: None)
    monkeypatch.setattr(launcher, "_owned_lock", contextlib.nullcontext)
    monkeypatch.setattr(launcher, "_database", lambda: repository)
    monkeypatch.setattr(launcher, "_read_key", lambda: pytest.fail("credential read"))
    assert launcher.run_one_shot()["error_code"] == "TARGET_NOT_EMPTY"
    assert len(repository.source_runs()) == 1


def test_fixture_launch_returns_only_canonical_receipt_and_private_environment(
    tmp_path, monkeypatch, capsys
):
    request_fixture(tmp_path, monkeypatch)
    repository = migrated_repository(tmp_path / "launched.sqlite")
    monkeypatch.setattr(launcher.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "_verify_runtime", lambda: None)
    monkeypatch.setattr(launcher, "_owned_lock", contextlib.nullcontext)
    monkeypatch.setattr(launcher, "_database", lambda: repository)
    monkeypatch.setattr(launcher, "_read_key", lambda: DUMMY)
    relay = types.SimpleNamespace(port=1234, proxy_url="http://127.0.0.1:1234")
    monkeypatch.setattr(launcher, "_relay", lambda _policy: contextlib.nullcontext(relay))
    invocations = []

    class FixtureProcess(FakeProcess):
        def communicate(self, *, timeout):
            AssemblyRosterEnumerator(
                three_member_api().connector(), repository.application
            ).enumerate()
            return super().communicate(timeout=timeout)

    def launch(argv, **kwargs):
        invocations.append(argv)
        assert kwargs["env"] == launcher._child_environment(DUMMY, relay.proxy_url)
        assert kwargs["stdout"] == kwargs["stderr"] == subprocess.PIPE
        assert kwargs["start_new_session"] is True
        return FixtureProcess()

    monkeypatch.setattr(subprocess, "Popen", launch)
    assert launcher.main([]) == 0
    assert len(invocations) == 1
    output = capsys.readouterr().out
    assert DUMMY not in output and str(tmp_path) not in output
    receipt = json.loads(output)
    assert receipt["status"] == "SUCCESS"
    assert receipt["canonical"]["observation_count"] == 3
    assert receipt["canonical"]["checkpoint"] == "2"


def test_partial_receipt_preserves_committed_checkpoint(tmp_path):
    from packages.connectors.open_assembly import (
        AssemblyRequestBudgetExceeded,
        AssemblyRequestLimits,
    )
    from tests.test_assembly_request_limits import FakeClock, bounded_connector

    repository = migrated_repository(tmp_path / "partial.sqlite")
    connector = bounded_connector(three_member_api(), FakeClock(), AssemblyRequestLimits(1, 0, 10))
    with pytest.raises(AssemblyRequestBudgetExceeded):
        AssemblyRosterEnumerator(connector, repository.application).enumerate()
    receipt = launcher._canonical_receipt(repository, OUTCOME | {"exit_code": 1})
    assert receipt["status"] == "COMPLETED_WITH_FAILURE"
    assert receipt["canonical"]["status"] == "PARTIAL"
    assert receipt["canonical"]["checkpoint"] == "1"
    assert receipt["canonical"]["observation_count"] == 2
