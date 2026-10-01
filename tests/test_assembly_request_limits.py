from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from packages.connectors.open_assembly import (
    AssemblyApiError,
    AssemblyRequestBudgetExceeded,
    AssemblyRequestLimits,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence.models import SourceRow, SourceSnapshotRow
from packages.verification.policy import PolicyDenied
from tests.test_batch_assembly import SECRET, migrated_repository, three_member_api
from workers.assembly_roster import AssemblyRosterEnumerator


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def bounded_connector(api, clock, limits, *, duration=0.0, starts=None):
    def handle(request: httpx.Request) -> httpx.Response:
        if starts is not None:
            starts.append(clock.now)
        clock.now += duration
        return api.handle(request)

    return OpenAssemblyMemberConnector(
        api_key=SECRET,
        page_size=2,
        transport=httpx.MockTransport(handle),
        request_limits=limits,
        clock=clock,
        sleeper=clock.sleep,
    )


@pytest.mark.parametrize("value", [0, -1, 1.5, True, float("inf"), float("nan"), "1"])
def test_request_count_requires_positive_integer(value) -> None:
    with pytest.raises(ValueError, match="max_requests"):
        AssemblyRequestLimits(value, 0, 5)


@pytest.mark.parametrize("value", [-1, float("inf"), float("-inf"), float("nan"), True, "1"])
def test_interval_requires_nonnegative_finite_number(value) -> None:
    with pytest.raises(ValueError, match="min_interval_seconds"):
        AssemblyRequestLimits(1, value, 5)


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("-inf"), float("nan"), True, "1"])
def test_deadline_requires_positive_finite_number(value) -> None:
    with pytest.raises(ValueError, match="deadline_seconds"):
        AssemblyRequestLimits(1, 0, value)


def test_limits_are_frozen() -> None:
    limits = AssemblyRequestLimits(1, 0, 5)
    with pytest.raises(FrozenInstanceError):
        limits.max_requests = 2  # type: ignore[misc]


def test_bounded_multipage_success_preserves_coverage_and_spacing(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "bounded-success.db")
    api = three_member_api()
    clock = FakeClock()
    starts: list[float] = []
    connector = bounded_connector(
        api, clock, AssemblyRequestLimits(2, 2, 5), duration=0.5, starts=starts
    )
    result = AssemblyRosterEnumerator(connector, repository.application).enumerate()
    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert api.calls == [1, 2]
    assert starts == [0, 2]
    assert clock.sleeps == [1.5]
    assert result.run.checkpoint_after == "2"
    assert repository.people() == []
    assert repository.claims() == []


def test_request_count_stop_preserves_last_committed_checkpoint(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "count-partial.db")
    api = three_member_api()
    connector = bounded_connector(api, FakeClock(), AssemblyRequestLimits(1, 0, 10))
    with pytest.raises(AssemblyRequestBudgetExceeded) as failure:
        AssemblyRosterEnumerator(connector, repository.application).enumerate()
    assert str(failure.value) == "National Assembly member API request budget exceeded"
    assert api.calls == [1]
    run = repository.source_runs()[-1]
    checkpoint = repository.source_checkpoint(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert run.status == SourceRunStatus.PARTIAL
    assert run.error_code == "AssemblyRequestBudgetExceeded"
    assert run.error_summary == "Assembly enumeration did not complete"
    assert run.records_seen == 2
    assert run.observations_created == 2
    assert run.checkpoint_after == "1"
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert set(checkpoint.metadata["seen_provider_hashes"]) == {"M-001", "M-002"}
    observations = repository.feeder_observations(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert len(observations) == 2
    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == len(snapshots) == 1
    stored = repr(run.model_dump(mode="json")) + repr(checkpoint.model_dump(mode="json"))
    stored += repr([item.model_dump(mode="json") for item in observations])
    stored += repr([item.url for item in sources])
    stored += repr([(item.fulltext, item.metadata_json) for item in snapshots])
    assert SECRET not in stored
    assert "KEY=" not in stored
    assert "TEL_NO" not in stored and "E_MAIL" not in stored


def test_first_attempt_deadline_fails_without_checkpoint_or_page_data(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "deadline-failed.db")
    api = three_member_api()
    connector = bounded_connector(api, FakeClock(), AssemblyRequestLimits(2, 0, 1), duration=1)
    with pytest.raises(AssemblyRequestBudgetExceeded):
        AssemblyRosterEnumerator(connector, repository.application).enumerate()
    assert api.calls == [1]
    run = repository.source_runs()[-1]
    assert run.status == SourceRunStatus.FAILED
    assert run.error_code == "AssemblyRequestBudgetExceeded"
    assert run.records_seen == run.observations_created == 0
    assert run.checkpoint_after is None
    assert (
        repository.source_checkpoint(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
        is None
    )
    assert (
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
        == []
    )
    with repository.sessions() as session:
        assert list(session.scalars(select(SourceRow))) == []
        assert list(session.scalars(select(SourceSnapshotRow))) == []
    assert SECRET not in repr(run.model_dump(mode="json"))


def test_second_response_deadline_does_not_commit_late_page(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "late-page.db")
    api = three_member_api()
    connector = bounded_connector(api, FakeClock(), AssemblyRequestLimits(2, 0, 1.5), duration=1)
    with pytest.raises(AssemblyRequestBudgetExceeded):
        AssemblyRosterEnumerator(connector, repository.application).enumerate()
    assert api.calls == [1, 2]
    run = repository.source_runs()[-1]
    assert run.status == SourceRunStatus.PARTIAL
    assert run.checkpoint_after == "1"
    assert run.records_seen == 2
    assert (
        repository.source_checkpoint(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        ).cursor
        == "1"
    )


def test_spacing_that_cannot_fit_deadline_stops_before_next_http() -> None:
    api = three_member_api()
    clock = FakeClock()
    connector = bounded_connector(api, clock, AssemblyRequestLimits(2, 2, 2))
    connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyRequestBudgetExceeded):
        connector.fetch(connector.discover()[0])
    assert api.calls == [1]
    assert clock.sleeps == []


def test_deadline_before_first_http_attempt_fails_without_network(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "pre-request-deadline.db")
    api = three_member_api()
    ticks = iter((0.0, 1.0))
    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(api.handle),
        request_limits=AssemblyRequestLimits(1, 0, 1),
        clock=lambda: next(ticks),
    )
    with pytest.raises(AssemblyRequestBudgetExceeded):
        AssemblyRosterEnumerator(connector, repository.application).enumerate()
    assert api.calls == []
    run = repository.source_runs()[-1]
    assert run.status == SourceRunStatus.FAILED
    assert run.checkpoint_after is None
    assert run.records_seen == 0


def test_oversleep_checks_deadline_before_attempt() -> None:
    api = three_member_api()
    clock = FakeClock()
    connector = bounded_connector(api, clock, AssemblyRequestLimits(2, 1, 3))
    connector._sleeper = lambda seconds: clock.sleep(seconds + 3)
    connector.fetch(connector.discover()[0])
    with pytest.raises(AssemblyRequestBudgetExceeded):
        connector.fetch(connector.discover()[0])
    assert api.calls == [1]


def test_remaining_deadline_shrinks_http_timeout() -> None:
    clock = FakeClock()
    timeouts: list[dict[str, float]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"])
        clock.now += 1
        return three_member_api().handle(request)

    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(handle),
        request_limits=AssemblyRequestLimits(2, 0, 4),
        clock=clock,
        sleeper=clock.sleep,
    )
    connector.fetch(connector.discover()[0])
    connector.fetch(connector.discover()[0])
    assert timeouts == [dict.fromkeys(timeouts[0], 4.0), dict.fromkeys(timeouts[1], 3.0)]


def test_failed_http_attempt_uses_request_count_without_leaking_key() -> None:
    api = three_member_api()
    api.fail_pages = {1}
    connector = bounded_connector(api, FakeClock(), AssemblyRequestLimits(1, 0, 5))
    with pytest.raises(AssemblyApiError, match="API request failed") as failure:
        connector.fetch(connector.discover()[0])
    assert SECRET not in str(failure.value)
    with pytest.raises(AssemblyRequestBudgetExceeded):
        connector.fetch(connector.discover()[0])
    assert api.calls == [1]


def test_budget_error_survives_http_error_masking() -> None:
    clock = FakeClock()

    def handle(request: httpx.Request) -> httpx.Response:
        clock.now += 2
        raise httpx.ReadTimeout(f"fixture-only failure {SECRET}", request=request)

    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        transport=httpx.MockTransport(handle),
        request_limits=AssemblyRequestLimits(1, 0, 1),
        clock=clock,
        sleeper=clock.sleep,
    )
    with pytest.raises(AssemblyRequestBudgetExceeded) as failure:
        connector.fetch(connector.discover()[0])
    assert SECRET not in str(failure.value)


def test_default_none_preserves_unbounded_connector_behavior() -> None:
    api = three_member_api()
    clock = FakeClock()
    connector = bounded_connector(api, clock, None, duration=100)
    for _ in range(3):
        connector.fetch(connector.discover()[0])
    assert api.calls == [1, 1, 1]
    assert clock.sleeps == []


def test_policy_denial_precedes_budget_and_http(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "blocked.db")
    api = three_member_api()
    connector = bounded_connector(api, FakeClock(), AssemblyRequestLimits(1, 0, 1))
    policy = national_assembly_member_policy().model_copy(
        update={"can_fetch": False, "collection_mode": SourceCollectionMode.BLOCKED}
    )
    with pytest.raises(PolicyDenied):
        AssemblyRosterEnumerator(connector, repository.application, policy).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []
