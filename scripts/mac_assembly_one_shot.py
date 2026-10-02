"""Pinned trusted Mac parent for one canonical Assembly acquisition, without retries.

The owned advisory lock coordinates this launcher only; it is not a universal collector
lease. A forced stop leaves canonical data untouched and requires human recovery review.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import signal
import stat
import subprocess
import sys
import zipfile
from collections.abc import Iterator, Sequence
from pathlib import Path, PurePosixPath

ROOT = Path("/Users/lee/Developer/civic-intel-collector-20261001/bounded-333aa26")
TARGET = Path("/Volumes/data/civic-intel/staging/assembly-one-shot-333aa26.sqlite")
TARGET_ALIAS = "mac-ssd-assembly-one-shot-333aa26"
REQUEST_SHA256 = "b127f5f10c596a78f9d370cde269a158b574e321c5502b33f29307420241b0ae"
WHEEL_SHA256 = "f94bd36a38c886da82b226301a6191000b8f4ad94c6747bd8f76a94c9f3d9cca"
RELAY_SHA256 = "41105315eb56979e66d4aaf6cdc2a122427084e582f0e204258b964ecf9b64ab"
CODE_COMMIT = "333aa26bda5f1110e53190f27de0c62a0f43cb30"
MANIFEST_SHA256 = "620a58365e748ebe987eefcb65d96ecb8b52bd58b83365e4b37b250d30541775"
FEEDER, SCOPE = "national_assembly_members", "current_member_roster"


class PreflightError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _no_symlinks(path: Path) -> None:
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise PreflightError("UNSAFE_PATH")


def _owned(info: os.stat_result, mode: int, *, directory: bool = False) -> None:
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if (
        not kind(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != mode
        or (not directory and info.st_nlink != 1)
    ):
        raise PreflightError("UNSAFE_FILE")


def _read_key() -> str:
    parent = ROOT / "credentials"
    _no_symlinks(parent)
    try:
        parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _owned(os.fstat(parent_fd), 0o700, directory=True)
            fd = os.open("assembly-api-key.txt", os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
            try:
                info = os.fstat(fd)
                _owned(info, 0o600)
                if not 1 <= info.st_size <= 1024:
                    raise PreflightError("UNSAFE_CREDENTIAL")
                value = os.read(fd, 1025).decode("ascii").strip()
                if not value or any(not 33 <= ord(char) <= 126 for char in value):
                    raise PreflightError("UNSAFE_CREDENTIAL")
                return value
            finally:
                os.close(fd)
        finally:
            os.close(parent_fd)
    except FileNotFoundError:
        raise PreflightError("CREDENTIAL_MISSING") from None
    except (OSError, UnicodeError, PreflightError):
        raise PreflightError("UNSAFE_CREDENTIAL") from None


def _request() -> dict:
    path = ROOT / "requests/assembly-one-shot.json"
    _no_symlinks(path)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != REQUEST_SHA256:
        raise PreflightError("REQUEST_DRIFT")
    request = json.loads(raw)
    if request["live_run_authorized"] is not True or request["target"] != TARGET_ALIAS:
        raise PreflightError("REQUEST_NOT_APPROVED")
    return request


def _verify_runtime() -> None:
    release = ROOT / "release"
    _no_symlinks(release)
    _no_symlinks(release / "manifest.json")
    manifest = json.loads((release / "manifest.json").read_bytes())
    canonical_manifest = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical_manifest).hexdigest() != MANIFEST_SHA256:
        raise PreflightError("RUNTIME_DRIFT")
    if manifest["code_commit"] != CODE_COMMIT or manifest["wheel_sha256"] != WHEEL_SHA256:
        raise PreflightError("RUNTIME_DRIFT")
    payloads = manifest["file_sha256"]
    if len(payloads) != 13:
        raise PreflightError("RUNTIME_DRIFT")
    for name, expected in payloads.items():
        relative = PurePosixPath(name)
        if relative.is_absolute() or ".." in relative.parts:
            raise PreflightError("RUNTIME_DRIFT")
        path = release / name
        _no_symlinks(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise PreflightError("RUNTIME_DRIFT")
    wheel = release / "civic_intel-0.1.0-py3-none-any.whl"
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != WHEEL_SHA256:
        raise PreflightError("RUNTIME_DRIFT")
    installed = importlib.metadata.distribution("civic-intel")
    if not Path(str(installed.locate_file(""))).is_relative_to(ROOT / "venv"):
        raise PreflightError("WRONG_RUNTIME")
    expected_python: set[str] = set()
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith(".py"):
                expected_python.add(name)
                path = Path(str(installed.locate_file(name)))
                _no_symlinks(path)
                if path.read_bytes() != archive.read(name):
                    raise PreflightError("INSTALLED_CODE_DRIFT")
    actual_python = {
        path.relative_to(Path(str(installed.locate_file("")))).as_posix()
        for package in ("apps", "packages", "workers")
        for path in Path(str(installed.locate_file(package))).rglob("*.py")
    }
    if actual_python != expected_python:
        raise PreflightError("INSTALLED_CODE_DRIFT")
    relay = ROOT / "assembly-egress.py"
    _no_symlinks(relay)
    if hashlib.sha256(relay.read_bytes()).hexdigest() != RELAY_SHA256:
        raise PreflightError("RELAY_DRIFT")
    if Path(sys.executable).resolve() != (ROOT / "venv/bin/python").resolve():
        raise PreflightError("WRONG_RUNTIME")


def _policy(request: dict):
    from packages.connectors.open_assembly import national_assembly_member_policy
    from packages.verification.policy import PolicyAction, require_policy

    policy = national_assembly_member_policy()
    contract = request["source_policy"]
    if (
        str(policy.id) != contract["id"]
        or policy.terms_checked_at is None
        or policy.terms_checked_at.isoformat().replace("+00:00", "Z")
        != contract["terms_checked_at"]
        or policy.domain != "open.assembly.go.kr"
    ):
        raise PreflightError("POLICY_DRIFT")
    require_policy(policy, PolicyAction.FETCH)
    require_policy(policy, PolicyAction.STORE_METADATA)
    return policy


@contextlib.contextmanager
def _owned_lock() -> Iterator[None]:
    import fcntl

    _no_symlinks(TARGET)
    _owned(TARGET.parent.stat(), 0o700, directory=True)
    fd = os.open(TARGET.with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        _owned(os.fstat(fd), 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PreflightError("LAUNCHER_BUSY") from None
        yield
    finally:
        os.close(fd)


def _database():
    from packages.persistence.database import Database

    _no_symlinks(TARGET)
    _owned(TARGET.stat(), 0o600)
    database = Database("sqlite:///" + str(TARGET))
    try:
        database.assert_ready()
        if database.schema_revision() != "0008":
            raise PreflightError("SCHEMA_MISMATCH")
        return database
    except Exception:
        database.close()
        raise


def _pristine(database) -> None:
    from sqlalchemy import func, select

    from packages.persistence.models import Base

    # Read existing canonical tables only; no creation, migration or direct SQL writes.
    with database.engine.connect() as connection:
        if any(
            connection.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        ):
            raise PreflightError("TARGET_NOT_EMPTY")


def _relay(policy):
    spec = importlib.util.spec_from_file_location("assembly_egress", ROOT / "assembly-egress.py")
    if spec is None or spec.loader is None:
        raise PreflightError("RELAY_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.AssemblyEgressRelay(
        max_connections=8,
        max_bytes_per_connection=4194304,
        max_seconds_per_connection=60,
        serve_seconds=180,
        policy=policy,
    )


def _sandbox(port: int) -> str:
    literals = [str(TARGET) + suffix for suffix in ("", "-journal", "-wal", "-shm")]
    read = " ".join(f"(literal {json.dumps(path)})" for path in literals)
    runtime = json.dumps(str(ROOT / "venv"))
    return (
        "(version 1)\n(deny default)\n(allow process-exec process-fork sysctl-read mach-lookup)\n"
        '(allow file-read* (subpath "/System") (subpath "/usr") (subpath "/bin") '
        '(subpath "/Library") (subpath "/opt/homebrew") (subpath "/private/var/db") '
        f'(subpath {runtime}) (literal "/dev/urandom") (literal "/dev/null") {read})\n'
        f'(allow file-write* (literal "/dev/null") {read})\n'
        f'(allow network-outbound (remote ip "localhost:{port}"))\n'
    )


def _child_environment(key: str, proxy_url: str) -> dict[str, str]:
    return {
        "HOME": "/Users/lee",
        "PATH": "/usr/bin:/bin",
        "TMPDIR": "/tmp",
        "PYTHONDONTWRITEBYTECODE": "1",
        "ASSEMBLY_API_KEY": key,
        "HTTPS_PROXY": proxy_url,
    }


def _command(port: int) -> list[str]:
    return [
        "/usr/bin/sandbox-exec",
        "-p",
        _sandbox(port),
        str(ROOT / "venv/bin/python"),
        "-I",
        "-B",
        "-c",
        "from apps.cli.main import main; raise SystemExit(main())",
        "observe",
        "assembly",
        "--allow-effect",
        "SOURCE_INGESTION",
        "--database-url",
        "sqlite:///" + str(TARGET),
        "--page-size",
        "100",
        "--max-requests",
        "8",
        "--min-request-interval",
        "1",
        "--fetch-deadline-seconds",
        "120",
    ]


def _watch(process: subprocess.Popen) -> dict:
    forced = False
    reaped = False
    try:
        process.communicate(timeout=180)
        reaped = True
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        forced = True
    finally:
        if not reaped:
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    pass
                try:
                    process.communicate(timeout=5)
                    reaped = True
                    break
                except subprocess.TimeoutExpired:
                    pass
    return {"exit_code": process.returncode, "forced_stop": forced, "process_reaped": reaped}


def _canonical_receipt(database, process: dict) -> dict:
    with database(read_only=True) as uow:
        runs = uow.acquisition.source_runs()
        checkpoint = uow.acquisition.source_checkpoint(FEEDER, SCOPE)
        observations = uow.acquisition.feeder_observations(FEEDER, SCOPE)
        runs_valid = len(runs) == 1 and runs[0].feeder == FEEDER and runs[0].scope_key == SCOPE
        run = runs[0] if runs_valid else None
        cursor = checkpoint.cursor if checkpoint else None
        safe_cursor = cursor if cursor in {None, *map(str, range(1, 9))} else None
        canonical = {
            "source_run_id": str(run.id) if run else None,
            "status": run.status.value if run else "UNAVAILABLE",
            "records_seen": run.records_seen if run else None,
            "observations_created": run.observations_created if run else None,
            "observations_unchanged": run.observations_unchanged if run else None,
            "observation_count": len(observations),
            "checkpoint": safe_cursor,
        }
        recovery = (
            process["forced_stop"]
            or not process["process_reaped"]
            or not runs_valid
            or canonical["status"] == "RUNNING"
            or cursor != safe_cursor
            or bool(uow.public.people() or uow.public.claims() or uow.public.organizations())
        )
        status = (
            "RECOVERY_REQUIRED"
            if recovery
            else "SUCCESS"
            if process["exit_code"] == 0 and canonical["status"] == "SUCCESS"
            else "COMPLETED_WITH_FAILURE"
        )
    return {"status": status, "target": TARGET_ALIAS, "process": process, "canonical": canonical}


def run_one_shot() -> dict:
    launched = False
    try:
        if sys.platform != "darwin":
            raise PreflightError("MAC_REQUIRED")
        request = _request()
        _verify_runtime()
        policy = _policy(request)
        with _owned_lock():
            database = _database()
            try:
                _pristine(database)
                key = _read_key()
                with _relay(policy) as relay:
                    # Recheck under our owned lock immediately before dispatch.
                    _pristine(database)
                    process = subprocess.Popen(
                        _command(relay.port),
                        cwd=ROOT / "release",
                        env=_child_environment(key, relay.proxy_url),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        start_new_session=True,
                    )
                    launched = True
                    key = ""
                    outcome = _watch(process)
                return _canonical_receipt(database, outcome)
            finally:
                database.close()
    except Exception as exc:  # noqa: BLE001 - trusted parent emits only fixed failure codes
        return {
            "status": "RECOVERY_REQUIRED" if launched else "BLOCKED",
            "error_code": exc.code if isinstance(exc, PreflightError) else "LAUNCHER_FAILED",
            "target": TARGET_ALIAS,
        }


def main(argv: Sequence[str] | None = None) -> int:
    if list(sys.argv[1:] if argv is None else argv):
        receipt = {"status": "BLOCKED", "error_code": "UNEXPECTED_ARGUMENTS"}
    else:
        receipt = run_one_shot()
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if receipt["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
