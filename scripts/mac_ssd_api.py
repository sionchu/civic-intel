"""Serve the canonical public API from a mounted, private SSD database.

This launcher never provisions, migrates, seeds, collects, materializes or publishes.
The database connection is read-only and the listener is loopback-only.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import plistlib
import sqlite3
import stat
import subprocess
import sys
from contextlib import closing
from pathlib import Path
from urllib.parse import quote


def check_target(volume: Path, database: Path, volume_uuid: str) -> tuple[int, int]:
    if sys.platform != "darwin" or not os.path.ismount(volume):
        raise ValueError("SSD_NOT_MOUNTED")
    info = subprocess.run(
        ["/usr/sbin/diskutil", "info", "-plist", str(volume)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    if plistlib.loads(info.stdout).get("VolumeUUID") != volume_uuid:
        raise ValueError("SSD_IDENTITY_MISMATCH")
    if database.is_symlink() or not database.resolve().is_relative_to(volume.resolve()):
        raise ValueError("DATABASE_PATH_DENIED")
    status = database.stat()
    if not stat.S_ISREG(status.st_mode) or status.st_mode & 0o077:
        raise ValueError("DATABASE_PERMISSIONS_DENIED")
    if status.st_uid != os.getuid() or status.st_dev != volume.stat().st_dev:
        raise ValueError("DATABASE_OWNER_OR_VOLUME_MISMATCH")
    with closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as connection:
        if connection.execute("SELECT version_num FROM alembic_version").fetchone() != ("0008",):
            raise ValueError("SCHEMA_HEAD_MISMATCH")
    return status.st_dev, status.st_ino


class MountedDatabase:
    """Reject requests after disconnection or replacement of the allocated file."""

    def __init__(self, app, volume: Path, database: Path, identity: tuple[int, int]):
        self.app, self.volume, self.database, self.identity = app, volume, database, identity

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            try:
                current = self.database.stat()
                available = (
                    os.path.ismount(self.volume)
                    and (current.st_dev, current.st_ino) == self.identity
                )
            except OSError:
                available = False
            if not available:
                body = b'{"error":{"code":"SERVICE_UNAVAILABLE","message":"Data storage is unavailable."}}'
                await send(
                    {
                        "type": "http.response.start",
                        "status": 503,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"cache-control", b"no-store"),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", type=Path, required=True)
    parser.add_argument("--volume-uuid", required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        if not 1024 <= args.port <= 65535:
            raise ValueError("INVALID_PORT")
        runtime_environment = {
            name: os.environ[name]
            for name in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL")
            if name in os.environ
        }
        os.environ.clear()
        os.environ.update(runtime_environment)
        identity = check_target(args.volume, args.database, args.volume_uuid)
        os.environ["DATABASE_URL"] = (
            "sqlite:///file:" + quote(str(args.database), safe="/") + "?mode=ro&uri=true"
        )
        import uvicorn

        from apps.api.main import app

        # Runtime receipts contain stable states only, never SQL parameters or tracebacks.
        logging.disable(logging.CRITICAL)
        print(
            json.dumps(
                {
                    "status": "API_STARTING",
                    "host": "127.0.0.1",
                    "port": args.port,
                    "schema": "0008",
                    "database_read_only": True,
                }
            ),
            flush=True,
        )
        uvicorn.run(
            MountedDatabase(app, args.volume, args.database, identity),
            host="127.0.0.1",
            port=args.port,
            workers=1,
            access_log=False,
            log_config=None,
        )
        return 0
    except (Exception, SystemExit):  # noqa: BLE001 -- sanitized process boundary
        print('{"status":"FAILED","error_code":"SSD_API_START_FAILED"}', flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
