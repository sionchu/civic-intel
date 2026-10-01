from __future__ import annotations

import socket
import threading
from collections.abc import Iterator

import pytest

from packages.connectors.open_assembly import national_assembly_member_policy
from packages.verification.policy import PolicyDenied
from scripts import mac_assembly_egress as egress

CONNECT = b"CONNECT open.assembly.go.kr:443 HTTP/1.1\r\nHost: open.assembly.go.kr:443\r\n\r\n"
DUMMY_SECRET = "fixture-key-never-log"


@pytest.fixture
def echo() -> Iterator[tuple[int, list[bytes]]]:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    listener.settimeout(0.1)
    stopped = threading.Event()
    received: list[bytes] = []
    active: list[socket.socket] = []

    def serve() -> None:
        while not stopped.is_set():
            try:
                connection, _ = listener.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            active.append(connection)
            with connection:
                connection.settimeout(0.1)
                while not stopped.is_set():
                    try:
                        data = connection.recv(65536)
                        if not data:
                            break
                        received.append(data)
                        connection.sendall(data)
                    except TimeoutError:
                        continue
                    except OSError:
                        break

    thread = threading.Thread(target=serve)
    thread.start()
    try:
        yield listener.getsockname()[1], received
    finally:
        stopped.set()
        listener.close()
        for connection in active:
            connection.close()
        thread.join(2)
        assert not thread.is_alive()


def relay_for(echo, **limits):
    port, _ = echo
    calls: list[float] = []

    def dial(timeout: float) -> socket.socket:
        calls.append(timeout)
        return socket.create_connection(("127.0.0.1", port), timeout=timeout)

    configuration = {
        "max_connections": 1,
        "max_bytes_per_connection": 4096,
        "max_seconds_per_connection": 2,
        "serve_seconds": 3,
    } | limits
    return egress.AssemblyEgressRelay(dialer=dial, **configuration), calls


def connect_client(relay) -> socket.socket:
    return socket.create_connection(("127.0.0.1", relay.port), timeout=2)


def header(connection: socket.socket) -> bytes:
    data = bytearray()
    while not data.endswith(b"\r\n\r\n"):
        part = connection.recv(1)
        if not part:
            break
        data.extend(part)
    return bytes(data)


def until_closed(connection: socket.socket) -> bytes:
    parts: list[bytes] = []
    while True:
        try:
            data = connection.recv(4096)
        except ConnectionResetError:
            break
        if not data:
            break
        parts.append(data)
    return b"".join(parts)


def test_exact_connect_relays_opaque_bytes_without_header_leak(echo, capsys) -> None:
    relay, calls = relay_for(echo)
    opaque = b"\x16\x03\x03\x00\x07\xff\x00\x80fixture"
    with relay:
        assert relay.proxy_url == f"http://127.0.0.1:{relay.port}"
        assert relay._listener.getsockname()[0] == "127.0.0.1"
        with connect_client(relay) as client:
            # Pipeline bytes to prove the CONNECT reader does not consume a TLS prefix.
            client.sendall(CONNECT + opaque)
            assert header(client) == egress._OK
            assert client.recv(len(opaque)) == opaque
    assert len(calls) == 1
    assert b"".join(echo[1]) == opaque
    assert relay.bytes_relayed == 2 * len(opaque)
    assert not relay._thread.is_alive()
    assert not relay._sockets
    capture = capsys.readouterr()
    assert capture.out == capture.err == ""


@pytest.mark.parametrize(
    "line",
    [
        b"GET / HTTP/1.1",
        b"POST https://open.assembly.go.kr/ HTTP/1.1",
        b"CONNECT example.com:443 HTTP/1.1",
        b"CONNECT open.assembly.go.kr:80 HTTP/1.1",
        b"CONNECT open.assembly.go.kr:0443 HTTP/1.1",
        b"CONNECT open.assembly.go.kr:443/path HTTP/1.1",
        b"CONNECT open.assembly.go.kr:443?key=fixture HTTP/1.1",
        b"CONNECT user@open.assembly.go.kr:443 HTTP/1.1",
        b"CONNECT open.assembly.go.kr.evil.invalid:443 HTTP/1.1",
        b"CONNECT open.assembly.go.kr.:443 HTTP/1.1",
        b"CONNECT OPEN.ASSEMBLY.GO.KR:443 HTTP/1.1",
        b"CONNECT https://open.assembly.go.kr:443 HTTP/1.1",
        b"CONNECT 127.0.0.1:443 HTTP/1.1",
        b"CONNECT [::1]:443 HTTP/1.1",
        b"CONNECT open.assembly.go.kr:443 HTTP/1.0",
        b"CONNECT  open.assembly.go.kr:443 HTTP/1.1",
        b"connect open.assembly.go.kr:443 HTTP/1.1",
    ],
)
def test_rejected_request_never_dials(echo, line: bytes, capsys) -> None:
    relay, calls = relay_for(echo)
    with relay, connect_client(relay) as client:
        client.sendall(line + b"\r\nX-Fixture: " + DUMMY_SECRET.encode() + b"\r\n\r\n")
        assert header(client) == egress._DENIED
    assert calls == []
    assert echo[1] == []
    capture = capsys.readouterr()
    assert capture.out == capture.err == ""


def test_connection_budget_counts_rejected_connections_and_stops_listener(echo) -> None:
    relay, calls = relay_for(echo)
    with relay:
        with connect_client(relay) as client:
            client.sendall(b"GET / HTTP/1.1\r\n\r\n")
            assert header(client) == egress._DENIED
        relay.wait()
        with pytest.raises(OSError):
            connect_client(relay)
    assert relay.connections_accepted == 1
    assert calls == []


def test_byte_budget_limits_total_forwarded_octets(echo) -> None:
    relay, calls = relay_for(echo, max_bytes_per_connection=4)
    with relay, connect_client(relay) as client:
        client.sendall(CONNECT)
        assert header(client) == egress._OK
        client.sendall(b"abcdefgh")
        assert until_closed(client) == b""
    assert len(calls) == 1
    assert b"".join(echo[1]) == b"abcd"
    assert relay.bytes_relayed == 4


def test_tunnel_time_budget_closes_idle_connection(echo) -> None:
    relay, calls = relay_for(echo, max_seconds_per_connection=0.15)
    with relay, connect_client(relay) as client:
        client.sendall(CONNECT)
        assert header(client) == egress._OK
        assert until_closed(client) == b""
    assert len(calls) == 1
    assert not relay._thread.is_alive()


def test_byte_budget_sums_both_directions(echo) -> None:
    relay, _ = relay_for(echo, max_bytes_per_connection=8)
    with relay, connect_client(relay) as client:
        client.sendall(CONNECT)
        assert header(client) == egress._OK
        client.sendall(b"abcd")
        assert until_closed(client) == b"abcd"
    assert relay.bytes_relayed == 8


def test_header_time_budget_does_not_dial(echo) -> None:
    relay, calls = relay_for(echo, max_seconds_per_connection=0.1)
    with relay, connect_client(relay) as client:
        client.sendall(b"CONNECT")
        assert until_closed(client) == b""
    assert calls == []


def test_header_size_budget_rejects_without_dial(echo) -> None:
    relay, calls = relay_for(echo)
    with relay, connect_client(relay) as client:
        client.sendall(b"CONNECT " + b"a" * 8184)
        assert header(client) == egress._DENIED
    assert calls == []


def test_close_interrupts_idle_tunnel_and_reaps_sockets(echo) -> None:
    relay, _ = relay_for(echo)
    with relay:
        with connect_client(relay) as client:
            client.sendall(CONNECT)
            assert header(client) == egress._OK
            relay.close()
            assert until_closed(client) == b""
        assert not relay._thread.is_alive()
        assert not relay._sockets
    relay.close()


def test_total_serve_budget_bounds_idle_listener(echo) -> None:
    relay, calls = relay_for(echo, serve_seconds=0.1)
    with relay:
        relay.wait()
        assert not relay._thread.is_alive()
    assert calls == []


def test_close_interrupts_partial_connect_header(echo) -> None:
    relay, calls = relay_for(echo)
    with relay, connect_client(relay) as client:
        client.sendall(b"CONNECT")
        relay.close()
        until_closed(client)
        assert not relay._thread.is_alive()
        assert not relay._sockets
    assert calls == []


@pytest.mark.parametrize("field", ["can_fetch", "can_store_metadata"])
def test_policy_denial_precedes_listener_creation(monkeypatch, field: str) -> None:
    policy = national_assembly_member_policy().model_copy(update={field: False})
    monkeypatch.setattr(socket, "socket", lambda *_a, **_k: pytest.fail("listener started"))
    with (
        pytest.raises(PolicyDenied),
        egress.AssemblyEgressRelay(
            max_connections=1,
            max_bytes_per_connection=10,
            max_seconds_per_connection=1,
            policy=policy,
        ),
    ):
        pytest.fail("policy must block")


@pytest.mark.parametrize("update", [{"domain": "example.com"}, {"id": None}])
def test_wrong_source_policy_cannot_start_listener(update) -> None:
    policy = national_assembly_member_policy().model_copy(update=update)
    with (
        pytest.raises(egress.AssemblyEgressError),
        egress.AssemblyEgressRelay(
            max_connections=1,
            max_bytes_per_connection=10,
            max_seconds_per_connection=1,
            policy=policy,
        ),
    ):
        pytest.fail("wrong source")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("max_connections", 0),
        ("max_connections", True),
        ("max_connections", 1.5),
        ("max_bytes_per_connection", -1),
        ("max_bytes_per_connection", True),
        ("max_seconds_per_connection", 0),
        ("max_seconds_per_connection", float("inf")),
        ("max_seconds_per_connection", float("nan")),
        ("serve_seconds", -1),
        ("serve_seconds", True),
        ("serve_seconds", float("inf")),
    ],
)
def test_invalid_budgets_fail_before_listener(name: str, value) -> None:
    limits = {
        "max_connections": 1,
        "max_bytes_per_connection": 10,
        "max_seconds_per_connection": 1,
        "serve_seconds": 1,
    } | {name: value}
    with pytest.raises(ValueError, match="positive and finite"):
        egress.AssemblyEgressRelay(**limits)


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "0.0.0.0", "224.0.0.1", "192.0.2.1"],
)
def test_default_dialer_rejects_nonpublic_ipv4_without_dial(monkeypatch, address: str) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_a, **_k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))],
    )
    monkeypatch.setattr(socket, "socket", lambda *_a: pytest.fail("nonpublic dial"))
    with pytest.raises(egress.AssemblyEgressError, match="Assembly egress unavailable"):
        egress._public_assembly_dial(1)


@pytest.mark.parametrize("address", ["::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1"])
def test_default_dialer_rejects_nonpublic_ipv6_without_dial(monkeypatch, address: str) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_a, **_k: [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", (address, 443, 0, 0))],
    )
    monkeypatch.setattr(socket, "socket", lambda *_a: pytest.fail("nonpublic dial"))
    with pytest.raises(egress.AssemblyEgressError):
        egress._public_assembly_dial(1)


def test_default_dialer_rejects_mixed_dns_answers_before_any_connection(monkeypatch) -> None:
    answers = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))
        for address in ("8.8.8.8", "127.0.0.1")
    ]
    monkeypatch.setattr(socket, "getaddrinfo", lambda *_a, **_k: answers)
    monkeypatch.setattr(socket, "socket", lambda *_a: pytest.fail("mixed answer dial"))
    with pytest.raises(egress.AssemblyEgressError):
        egress._public_assembly_dial(1)


def test_default_dialer_resolves_once_and_pins_numeric_address(monkeypatch) -> None:
    resolutions: list[tuple] = []
    connections: list[tuple] = []

    class FakeSocket:
        def settimeout(self, timeout: float) -> None:
            assert 0 < timeout <= 1

        def connect(self, address: tuple) -> None:
            connections.append(address)

        def close(self) -> None:
            pass

    upstream = FakeSocket()

    def resolve(*args, **kwargs):
        resolutions.append(args)
        assert kwargs == {"type": socket.SOCK_STREAM, "proto": socket.IPPROTO_TCP}
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(socket, "socket", lambda *_a: upstream)
    assert egress._public_assembly_dial(1) is upstream
    assert resolutions == [("open.assembly.go.kr", 443)]
    assert connections == [("8.8.8.8", 443)]


def test_dialer_errors_are_constant_and_never_logged(echo, capsys) -> None:
    relay, _ = relay_for(echo)

    def fail(_timeout: float) -> socket.socket:
        raise RuntimeError(f"https://open.assembly.go.kr/?KEY={DUMMY_SECRET}")

    relay._dialer = fail
    with relay, connect_client(relay) as client:
        client.sendall(CONNECT)
        assert header(client) == egress._UNAVAILABLE
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def test_default_dns_error_is_sanitized(monkeypatch) -> None:
    def fail(*_args, **_kwargs):
        raise OSError(DUMMY_SECRET)

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    with pytest.raises(egress.AssemblyEgressError) as failure:
        egress._public_assembly_dial(1)
    assert str(failure.value) == "Assembly egress unavailable"
    assert failure.value.__suppress_context__


def test_entrypoint_requires_bounded_serve_and_sanitizes_bad_arguments(capsys) -> None:
    assert egress.main(["--max-connections", DUMMY_SECRET]) == 1
    capture = capsys.readouterr()
    assert capture.out.strip() == '{"error_code": "ASSEMBLY_EGRESS_FAILED"}'
    assert capture.err == ""


def test_entrypoint_serves_for_bounded_duration_without_upstream(capsys) -> None:
    assert (
        egress.main(
            [
                "--max-connections",
                "1",
                "--max-bytes-per-connection",
                "10",
                "--max-seconds-per-connection",
                "0.1",
                "--serve-seconds",
                "0.1",
            ]
        )
        == 0
    )
    capture = capsys.readouterr()
    assert capture.out.startswith('{"proxy_url": "http://127.0.0.1:')
    assert capture.err == ""
