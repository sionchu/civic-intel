"""Bounded Assembly-only CONNECT relay; this is transport, not an acquisition runner.

TLS and certificate/hostname verification stay at the canonical HTTPS client. The relay
does not terminate TLS, inspect tunnel bytes, retain requests or log raw failures. A policy
decision is required but is not a live-source grant. Use only with separately approved
source access and a collector sandbox that permits this loopback port and no direct egress.
DNS resolution is not interruptible here; an external process watchdog remains necessary.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import select
import socket
import threading
import time
from collections.abc import Callable, Sequence
from typing import NoReturn, Self

from packages.connectors.open_assembly import national_assembly_member_policy
from packages.domain.contracts import SourcePolicy
from packages.domain.source_contracts import ASSEMBLY_MEMBER_HOST, ASSEMBLY_MEMBER_POLICY_ID
from packages.verification.policy import PolicyAction, require_policy

_TARGET = f"{ASSEMBLY_MEMBER_HOST}:443".encode("ascii")
_CONNECT_LINE = b"CONNECT " + _TARGET + b" HTTP/1.1"
_OK = b"HTTP/1.1 200 Connection Established\r\n\r\n"
_DENIED = b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
_UNAVAILABLE = b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"


class AssemblyEgressError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Assembly egress unavailable")


def _positive_seconds(value: float) -> bool:
    try:
        return not isinstance(value, bool) and math.isfinite(value) and value > 0
    except (TypeError, OverflowError):
        return False


def _public_assembly_dial(timeout: float) -> socket.socket:
    """Resolve once, reject mixed/nonpublic answers, then connect to a pinned numeric IP."""
    deadline = time.monotonic() + timeout
    try:
        answers = socket.getaddrinfo(
            ASSEMBLY_MEMBER_HOST, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
        )
        if not answers:
            raise AssemblyEgressError()
        for family, _, _, _, address in answers:
            ip = ipaddress.ip_address(address[0])
            if (
                family not in (socket.AF_INET, socket.AF_INET6)
                or not ip.is_global
                or ip.is_multicast
                or ip.is_reserved
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_unspecified
                or ip.is_private
                or (family == socket.AF_INET6 and (len(address) != 4 or address[-1] != 0))
            ):
                raise AssemblyEgressError()
        for family, kind, protocol, _, address in answers:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            upstream = socket.socket(family, kind, protocol)
            try:
                upstream.settimeout(remaining)
                # address came from the validated DNS result; no second hostname lookup.
                upstream.connect(address)
                return upstream
            except OSError:
                upstream.close()
        raise AssemblyEgressError()
    except (OSError, ValueError, AssemblyEgressError):
        raise AssemblyEgressError() from None


class AssemblyEgressRelay:
    """Serial loopback listener with bounded accepted connections and tunnel octets.

    The byte cap sums both tunnel directions, excluding CONNECT headers. Time includes
    header reading, dialing and tunneling. dialer is an offline-fixture seam, not an
    operator-configurable destination. Instances are single-use.
    """

    def __init__(
        self,
        *,
        max_connections: int,
        max_bytes_per_connection: int,
        max_seconds_per_connection: float,
        serve_seconds: float = 60,
        policy: SourcePolicy | None = None,
        dialer: Callable[[float], socket.socket] | None = None,
    ) -> None:
        if (
            type(max_connections) is not int
            or max_connections <= 0
            or type(max_bytes_per_connection) is not int
            or max_bytes_per_connection <= 0
            or not _positive_seconds(max_seconds_per_connection)
            or not _positive_seconds(serve_seconds)
        ):
            raise ValueError("Assembly egress limits must be positive and finite")
        self._policy = policy if policy is not None else national_assembly_member_policy()
        self._dialer = dialer if dialer is not None else _public_assembly_dial
        self._max_connections = max_connections
        self._max_bytes = max_bytes_per_connection
        self._connection_seconds = max_seconds_per_connection
        self._serve_seconds = serve_seconds
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._sockets: set[socket.socket] = set()
        self._thread: threading.Thread | None = None
        self.connections_accepted = 0
        self.bytes_relayed = 0

    def __enter__(self) -> Self:
        if self._thread is not None or self._stop.is_set():
            raise AssemblyEgressError()
        if (
            self._policy.id != ASSEMBLY_MEMBER_POLICY_ID
            or self._policy.domain != ASSEMBLY_MEMBER_HOST
        ):
            raise AssemblyEgressError()
        require_policy(self._policy, PolicyAction.FETCH)
        require_policy(self._policy, PolicyAction.STORE_METADATA)
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            listener.settimeout(0.1)
            self._listener = listener
            self.port = listener.getsockname()[1]
            self.proxy_url = f"http://127.0.0.1:{self.port}"
            self._serve_deadline = time.monotonic() + self._serve_seconds
            self._thread = threading.Thread(target=self._serve, daemon=True)
            self._thread.start()
            return self
        except OSError:
            listener.close()
            raise AssemblyEgressError() from None

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _track(self, connection: socket.socket) -> None:
        with self._lock:
            if self._stop.is_set():
                connection.close()
                raise AssemblyEgressError()
            self._sockets.add(connection)

    def _serve(self) -> None:
        try:
            while (
                not self._stop.is_set()
                and time.monotonic() < self._serve_deadline
                and self.connections_accepted < self._max_connections
            ):
                try:
                    client, _ = self._listener.accept()
                except TimeoutError:
                    continue
                except OSError:
                    break
                self.connections_accepted += 1
                self._handle(client)
        finally:
            self._listener.close()

    def _handle(self, client: socket.socket) -> None:
        upstream: socket.socket | None = None
        connected = False
        deadline = min(time.monotonic() + self._connection_seconds, self._serve_deadline)
        try:
            self._track(client)
            header = bytearray()
            # Avoid reading/decode of any pipelined TLS bytes beyond the header terminator.
            while not header.endswith(b"\r\n\r\n"):
                if len(header) >= 8192:
                    client.sendall(_DENIED)
                    return
                self._timeout(client, deadline)
                part = client.recv(1)
                if not part:
                    return
                header.extend(part)
            if bytes(header).split(b"\r\n", 1)[0] != _CONNECT_LINE:
                client.sendall(_DENIED)
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            upstream = self._dialer(remaining)
            self._track(upstream)
            self._timeout(client, deadline)
            client.sendall(_OK)
            connected = True
            self._tunnel(client, upstream, deadline)
        except TimeoutError:
            pass
        except Exception:  # noqa: BLE001 - do not expose arbitrary dialer errors from a thread
            # Never log/serialize raw request bytes, DNS/socket errors or dialer exceptions.
            if not connected:
                try:
                    self._timeout(client, deadline)
                    client.sendall(_UNAVAILABLE)
                except (OSError, AssemblyEgressError):
                    pass
        finally:
            for connection in (client, upstream):
                if connection is not None:
                    connection.close()
                    with self._lock:
                        self._sockets.discard(connection)

    def _timeout(self, connection: socket.socket, deadline: float) -> None:
        remaining = deadline - time.monotonic()
        if self._stop.is_set() or remaining <= 0:
            raise AssemblyEgressError()
        connection.settimeout(remaining)

    def _tunnel(self, client: socket.socket, upstream: socket.socket, deadline: float) -> None:
        transferred = 0
        while transferred < self._max_bytes and not self._stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            readable, _, _ = select.select([client, upstream], [], [], remaining)
            for source in readable:
                self._timeout(source, deadline)
                data = source.recv(min(65536, self._max_bytes - transferred))
                if not data:
                    return
                target = upstream if source is client else client
                self._timeout(target, deadline)
                target.sendall(data)
                transferred += len(data)
                self.bytes_relayed += len(data)
                if transferred >= self._max_bytes:
                    return

    def wait(self) -> None:
        if self._thread is None:
            raise AssemblyEgressError()
        self._thread.join(max(0.0, self._serve_deadline - time.monotonic()) + 0.2)
        self.close()

    def close(self) -> None:
        self._stop.set()
        if self._thread is None:
            return
        self._listener.close()
        with self._lock:
            for connection in self._sockets:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()
        self._thread.join(1)
        if self._thread.is_alive():
            raise AssemblyEgressError()


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError("Invalid Assembly egress arguments")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(description="Bounded Assembly-only loopback CONNECT transport")
    parser.add_argument("--max-connections", type=int, required=True)
    parser.add_argument("--max-bytes-per-connection", type=int, required=True)
    parser.add_argument("--max-seconds-per-connection", type=float, required=True)
    parser.add_argument("--serve-seconds", type=float, required=True)
    try:
        args = parser.parse_args(argv)
        with AssemblyEgressRelay(**vars(args)) as relay:
            print(json.dumps({"proxy_url": relay.proxy_url}), flush=True)
            relay.wait()
        return 0
    except Exception:  # noqa: BLE001 - the process boundary emits only a constant failure code
        print(json.dumps({"error_code": "ASSEMBLY_EGRESS_FAILED"}), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
