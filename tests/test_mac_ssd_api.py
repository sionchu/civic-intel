from __future__ import annotations

import asyncio
import json
import os
import plistlib
import sqlite3
import stat
from contextlib import closing
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import mac_ssd_api


@pytest.fixture
def target(tmp_path, monkeypatch):
    volume = tmp_path / "volume"
    volume.mkdir()
    database = volume / "assembly.sqlite"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
        connection.execute("INSERT INTO alembic_version VALUES ('0008')")
    database.chmod(0o600)
    monkeypatch.setattr(mac_ssd_api.sys, "platform", "darwin")
    monkeypatch.setattr(mac_ssd_api.os.path, "ismount", lambda path: path == volume)
    monkeypatch.setattr(mac_ssd_api.os, "getuid", lambda: database.stat().st_uid, raising=False)
    original_stat = Path.stat
    permissions = {"mode": 0o600}

    def posix_stat(path, *args, **kwargs):
        result = original_stat(path, *args, **kwargs)
        if path == database:
            values = list(result)
            values[0] = stat.S_IFREG | permissions["mode"]
            return os.stat_result(values)
        return result

    monkeypatch.setattr(Path, "stat", posix_stat)
    monkeypatch.setattr(
        mac_ssd_api.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(stdout=plistlib.dumps({"VolumeUUID": "allocated-volume"})),
    )
    return volume, database, permissions


def test_target_checks_do_not_modify_database(target):
    volume, database, _ = target
    before = database.read_bytes()
    identity = mac_ssd_api.check_target(volume, database, "allocated-volume")
    assert identity == (database.stat().st_dev, database.stat().st_ino)
    assert database.read_bytes() == before


@pytest.mark.parametrize(
    "failure", ["unmounted", "other_volume", "permissions", "schema", "missing"]
)
def test_target_fails_closed(target, monkeypatch, failure):
    volume, database, permissions = target
    expected_uuid = "allocated-volume"
    if failure == "unmounted":
        monkeypatch.setattr(mac_ssd_api.os.path, "ismount", lambda _: False)
    elif failure == "other_volume":
        expected_uuid = "different-volume"
    elif failure == "permissions":
        permissions["mode"] = 0o644
    elif failure == "schema":
        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("UPDATE alembic_version SET version_num='0007'")
    else:
        database.unlink()
    with pytest.raises((ValueError, OSError)):
        mac_ssd_api.check_target(volume, database, expected_uuid)
    if failure == "missing":
        assert not database.exists()


def test_runtime_rejects_disconnect_and_replacement(target, monkeypatch):
    volume, database, _ = target
    identity = mac_ssd_api.check_target(volume, database, "allocated-volume")
    called, responses = [], []

    async def app(scope, receive, send):
        called.append(scope["type"])

    async def send(response):
        responses.append(response)

    guard = mac_ssd_api.MountedDatabase(app, volume, database, identity)
    asyncio.run(guard({"type": "http"}, None, send))
    assert called == ["http"]
    database.rename(volume / "preserved.sqlite")
    database.write_bytes(b"replacement")
    asyncio.run(guard({"type": "http"}, None, send))
    assert called == ["http"]
    assert responses[0]["status"] == 503
    assert json.loads(responses[1]["body"])["error"]["code"] == "SERVICE_UNAVAILABLE"
    monkeypatch.setattr(mac_ssd_api.os.path, "ismount", lambda _: False)
    responses.clear()
    asyncio.run(guard({"type": "http"}, None, send))
    assert responses[0]["status"] == 503


@pytest.mark.parametrize("exit_code", [1, 3])
def test_uvicorn_startup_exit_is_reported_without_credentials(
    target, monkeypatch, capsys, exit_code
):
    volume, database, _ = target
    child_environments = []

    def diskutil(*args, **kwargs):
        child_environments.append(dict(mac_ssd_api.os.environ))
        return SimpleNamespace(stdout=plistlib.dumps({"VolumeUUID": "allocated-volume"}))

    monkeypatch.setattr(mac_ssd_api.subprocess, "run", diskutil)
    monkeypatch.setattr(
        mac_ssd_api.sys,
        "argv",
        [
            "mac_ssd_api.py",
            "--volume",
            str(volume),
            "--volume-uuid",
            "allocated-volume",
            "--database",
            str(database),
        ],
    )
    monkeypatch.setenv("ASSEMBLY_API_KEY", "fixture-secret-do-not-expose")
    # Isolate the launcher's environment replacement from the rest of the test process.
    monkeypatch.setattr(mac_ssd_api.os, "environ", dict(os.environ))
    monkeypatch.setattr(mac_ssd_api.logging, "disable", lambda _: None)
    monkeypatch.setitem(mac_ssd_api.sys.modules, "apps.api.main", SimpleNamespace(app=object()))

    def fail(*args, **kwargs):
        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["workers"] == 1
        assert "ASSEMBLY_API_KEY" not in mac_ssd_api.os.environ
        assert "mode=ro&uri=true" in mac_ssd_api.os.environ["DATABASE_URL"]
        raise SystemExit(exit_code)

    monkeypatch.setitem(mac_ssd_api.sys.modules, "uvicorn", SimpleNamespace(run=fail))
    assert mac_ssd_api.main() == 1
    assert len(child_environments) == 1
    assert "ASSEMBLY_API_KEY" not in child_environments[0]
    output = capsys.readouterr().out
    assert json.loads(output.splitlines()[-1])["error_code"] == "SSD_API_START_FAILED"
    assert "fixture-secret" not in output
