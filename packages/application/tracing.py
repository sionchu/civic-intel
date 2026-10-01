from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from time import monotonic
from typing import Protocol, TextIO
from uuid import uuid4


@dataclass(frozen=True)
class RunEvent:
    trace_id: str
    run_id: str
    parent_run_id: str | None
    name: str
    status: str
    duration_ms: int
    failure_code: str | None = None
    source_run_id: str | None = None


class TraceSink(Protocol):
    def emit(self, event: RunEvent) -> None: ...


class NullTraceSink:
    def emit(self, event: RunEvent) -> None:
        pass


_sink: ContextVar[TraceSink | None] = ContextVar("operational_trace_sink", default=None)


@contextmanager
def trace_sink_scope(sink: TraceSink) -> Iterator[None]:
    token = _sink.set(sink)
    try:
        yield
    finally:
        _sink.reset(token)


class JsonTraceSink:
    """Optional local operational diagnostics; never source evidence or raw payloads."""

    def __init__(self, stream: TextIO):
        self.stream = stream

    def emit(self, event: RunEvent) -> None:
        self.stream.write(json.dumps(asdict(event), sort_keys=True) + "\n")
        self.stream.flush()


class Trace:
    def __init__(self, sink: TraceSink | None = None):
        self.sink = sink or _sink.get() or NullTraceSink()
        self.trace_id = str(uuid4())
        self.root_run_id = str(uuid4())
        self.source_run_id: str | None = None

    @contextmanager
    def span(self, name: str, *, root: bool = False) -> Iterator[None]:
        run_id = self.root_run_id if root else str(uuid4())
        started = monotonic()
        status, failure = "SUCCESS", None
        try:
            yield
        except Exception as exc:
            status, failure = "FAILED", type(exc).__name__[:120]
            raise
        finally:
            # A diagnostics sink must not change the outcome of an evidence transaction.
            with suppress(Exception):
                self.sink.emit(
                    RunEvent(
                        self.trace_id,
                        run_id,
                        None if root else self.root_run_id,
                        name,
                        status,
                        int((monotonic() - started) * 1000),
                        failure,
                        self.source_run_id,
                    )
                )
