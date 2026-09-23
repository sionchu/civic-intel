"""Launch the existing Web/API privately; no DB writes or provider collection."""

from __future__ import annotations

import argparse
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from uuid import UUID

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]


def _available(port: int) -> bool:
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        # Only our recorded child process tree, including its owned private SSH forward.
        taskkill = str(Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/taskkill.exe")
        subprocess.run(
            [taskkill, "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def _private_uri(line: str, port: int) -> str | None:
    match = re.search(r"postgres(?:ql)?://[^\s\x1b]+", line)
    if match is None:
        return None
    value = match.group(0).strip("\"'")
    parsed = urlsplit(value)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port != port:
        raise RuntimeError("Railway returned a non-loopback database address")
    return value


def _railway_tunnel(project: str, processes: list[subprocess.Popen]) -> str:
    railway = shutil.which("railway")
    if not railway:
        raise RuntimeError("Railway CLI is required for a private staging tunnel")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    environment = os.environ.copy()
    if os.name == "nt":
        git_ssh = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/usr/bin"
        if (git_ssh / "ssh.exe").is_file():
            environment["PATH"] = str(git_ssh) + os.pathsep + environment.get("PATH", "")
    process = subprocess.Popen(
        [
            railway,
            "connect",
            "postgres",
            "--project",
            project,
            "--environment",
            "staging",
            "--tunnel-only",
            "--port",
            str(port),
        ],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    processes.append(process)
    lines: queue.Queue[str] = queue.Queue()

    def capture() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line[:10000])  # Never print or persist connection credentials.

    threading.Thread(target=capture, daemon=True).start()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            uri = _private_uri(lines.get(timeout=0.5), port)
            if uri:
                return uri
        except queue.Empty:
            if process.poll() is not None:
                break
    raise RuntimeError("Private Railway tunnel unavailable; verify CLI login and SSH locally")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Loopback-only read-only Civic Intel operator console"
    )
    parser.add_argument(
        "--label", choices=("LOCAL", "STAGING", "RESTORED", "TEST"), default="LOCAL"
    )
    parser.add_argument(
        "--railway-project",
        type=UUID,
        help="Optional explicit Railway project; opens its existing staging/postgres private tunnel",
    )
    parser.add_argument("--api-port", type=int, default=8310)
    parser.add_argument("--web-port", type=int, default=3310)
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Use the Next dev server instead of the built standalone artifact",
    )
    args = parser.parse_args(argv)
    if not os.environ.get("DATABASE_URL") and not args.railway_project:
        parser.error("Provide DATABASE_URL or --railway-project; no database is created or seeded")
    if os.environ.get("DATABASE_URL") and args.railway_project:
        parser.error("Choose DATABASE_URL or --railway-project, not both")
    if args.api_port == args.web_port or any(
        not 1024 <= p <= 65535 or not _available(p) for p in (args.api_port, args.web_port)
    ):
        parser.error("Use two available loopback ports between 1024 and 65535")
    node = shutil.which("node")
    if node is None:
        parser.error("Node.js is required")
    web_root = ROOT / "apps/web"
    script = web_root / (
        "node_modules/next/dist/bin/next" if args.dev else ".next/standalone/server.js"
    )
    if not script.exists():
        parser.error("Run npm --prefix apps/web ci and npm --prefix apps/web run build first")
    processes: list[subprocess.Popen] = []
    try:
        environment = os.environ.copy()
        if args.railway_project:
            environment["DATABASE_URL"] = _railway_tunnel(str(args.railway_project), processes)
            label = "STAGING"
        else:
            label = args.label
        parsed = make_url(environment["DATABASE_URL"])
        if parsed.get_backend_name() == "sqlite" and (
            not parsed.database or not Path(parsed.database).is_file()
        ):
            raise RuntimeError("An existing migrated SQLite database is required")
        environment.update(
            {
                "CIVIC_OPERATOR_ENABLED": "1",
                "CIVIC_OPERATOR_TOKEN": secrets.token_urlsafe(32),
                "CIVIC_OPERATOR_LABEL": label,
                "CIVIC_OPERATOR_API_URL": f"http://127.0.0.1:{args.api_port}",
                "CIVIC_API_URL": f"http://127.0.0.1:{args.api_port}",
                "CIVIC_INDEXING_ENABLED": "0",
                "HOSTNAME": "127.0.0.1",
                "PORT": str(args.web_port),
                "PYTHONIOENCODING": "utf-8",
            }
        )
        api = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.operator:create_operator_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.api_port),
                "--no-access-log",
            ],
            cwd=ROOT,
            env=environment,
        )
        processes.append(api)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if api.poll() is not None:
                raise RuntimeError("Private API failed to start")
            try:
                with urlopen(f"http://127.0.0.1:{args.api_port}/ready", timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Private API readiness timed out")
        web_command = [node, str(script)]
        if args.dev:
            web_command += ["dev", "--hostname", "127.0.0.1", "--port", str(args.web_port)]
        web = subprocess.Popen(web_command, cwd=web_root, env=environment)
        processes.append(web)
        print(f"Operator console: http://127.0.0.1:{args.web_port}/admin/review", flush=True)
        print(f"{label}, database read-only. Ctrl+C closes owned services/tunnel.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(1)
        return 1
    except KeyboardInterrupt:
        return 0
    except (OSError, ValueError, RuntimeError, SQLAlchemyError):
        print(
            "Operator startup/runtime failed. Verify DB readiness or Railway login/SSH; no DB change was requested.",
            file=sys.stderr,
        )
        return 1
    finally:
        for process in reversed(processes):
            _stop(process)


if __name__ == "__main__":
    raise SystemExit(main())
