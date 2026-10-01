import io
import json

import pytest

from packages.application.tracing import JsonTraceSink, Trace, trace_sink_scope
from tests.support import ScenarioDatabase
from tests.test_materialization import OnePageRoster, enumerate_rows, member_row
from tests.test_repository import migrate


def test_acquisition_trace_correlates_committed_run_without_source_payload(tmp_path):
    db = ScenarioDatabase(migrate(tmp_path / "trace.db"))
    stream = io.StringIO()
    with trace_sink_scope(JsonTraceSink(stream)):
        enumerate_rows(db, OnePageRoster([member_row("M-001", "비공개본문이름")]))
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    root = next(event for event in events if event["parent_run_id"] is None)
    children = [event for event in events if event["parent_run_id"] is not None]
    assert root["name"] == "observe-source"
    assert root["status"] == "SUCCESS"
    assert root["source_run_id"] == str(db.source_runs()[0].id)
    assert children
    assert all(event["trace_id"] == root["trace_id"] for event in events)
    assert all(event["parent_run_id"] == root["run_id"] for event in children)
    assert {"policy-check", "start-run", "page-commit", "coverage-verified"} <= {
        event["name"] for event in children
    }
    assert "비공개본문이름" not in stream.getvalue()
    assert "assembly-materialization-test-secret" not in stream.getvalue()


def test_trace_failure_is_redacted_and_sink_failure_does_not_change_outcome():
    stream = io.StringIO()
    trace = Trace(JsonTraceSink(stream))
    with pytest.raises(ValueError), trace.span("fixture", root=True):
        raise ValueError("password-private-source-contents")
    event = json.loads(stream.getvalue())
    assert event["status"] == "FAILED"
    assert event["failure_code"] == "ValueError"
    assert "private-source" not in stream.getvalue()

    class BrokenSink:
        def emit(self, event):
            raise OSError("fixture sink unavailable")

    with Trace(BrokenSink()).span("fixture", root=True):
        pass
    with (
        pytest.raises(ValueError, match="original outcome"),
        Trace(BrokenSink()).span("fixture", root=True),
    ):
        raise ValueError("original outcome")
