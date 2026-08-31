from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.nec_local_elections import (
    NecApiError,
    NecWinnerConnector,
    nec_local_election_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.local_elections import LocalElectionWinnerEnumerator, NecWinnerCoverageError

SECRET = "nec-batch-secret-must-not-persist"
SCOPE = "20260603:4"


def winner_row(
    candidate_id: str,
    name: str,
    *,
    party: str = "테스트당",
    votes: str = "12,345",
) -> dict[str, str]:
    return {
        "sgId": "20260603",
        "sgTypecode": "4",
        "huboid": candidate_id,
        "sggName": "테스트시장선거",
        "sdName": "경기도",
        "wiwName": "테스트시",
        "giho": "1",
        "gihoSangse": "",
        "jdName": party,
        "name": name,
        "hanjaName": f"{name}漢字",
        "gender": "남",
        "birthday": "19700102",
        "age": "56",
        "addr": "경기도 테스트시 비공개동",
        "jobId": "75",
        "job": "정당인",
        "eduId": "68",
        "edu": "테스트대학교 졸업",
        "career1": "(전) 테스트시의원",
        "career2": "-",
        "dugsu": votes,
        "dugyul": "52.10",
        "serviceKey": SECRET,
    }


class WinnerApi:
    def __init__(
        self,
        pages: dict[int, list[dict[str, str]]],
        *,
        totals: dict[int, int] | None = None,
        provider_pages: dict[int, int] | None = None,
        provider_sizes: dict[int, int] | None = None,
    ) -> None:
        self.pages = pages
        self.totals = totals or {}
        self.provider_pages = provider_pages or {}
        self.provider_sizes = provider_sizes or {}
        self.fail_pages: set[int] = set()
        self.calls: list[int] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.params["serviceKey"] == SECRET
        assert request.url.params["sgId"] == "20260603"
        assert request.url.params["sgTypecode"] == "4"
        assert "sdName" not in request.url.params
        assert "sggName" not in request.url.params
        page = int(request.url.params["pageNo"])
        page_size = int(request.url.params["numOfRows"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.pages.get(page, [])
        total = self.totals.get(page, sum(len(items) for items in self.pages.values()))
        payload = {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {
                    "pageNo": self.provider_pages.get(page, page),
                    "numOfRows": self.provider_sizes.get(page, page_size),
                    "totalCount": total,
                    "items": {"item": rows} if rows else {},
                },
            }
        }
        return httpx.Response(200, json=payload)

    def connector(self, *, page_size: int = 2) -> NecWinnerConnector:
        return NecWinnerConnector(
            election_id="20260603",
            election_type=4,
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def three_winner_api() -> WinnerApi:
    return WinnerApi(
        {
            1: [winner_row("C-001", "가당선"), winner_row("C-002", "나당선")],
            2: [winner_row("C-003", "다당선")],
        }
    )


def test_full_winner_enumeration_is_complete_private_field_free_and_exact(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "nec-winners.db")
    api = three_winner_api()

    result = LocalElectionWinnerEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(LocalElectionWinnerEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["expected_pages"] == 2
    assert checkpoint.metadata["total_count"] == 3

    observations = repository.feeder_observations(
        LocalElectionWinnerEnumerator.FEEDER, SCOPE
    )
    assert len(observations) == 3
    assert observations[0].identity_hints["external_ids"] == {"nec_huboid": "C-001"}
    assert observations[0].identity_hints["canonical_name"] == "가당선"
    assert observations[0].provider_observed_at is not None
    assert observations[0].provider_observed_at.date().isoformat() == "2026-06-03"
    persisted = repr([item.model_dump(mode="json") for item in observations])
    assert "addr" not in persisted.casefold()
    assert "address" not in persisted.casefold()
    assert "비공개동" not in persisted
    assert "gender" not in persisted
    assert "age" not in persisted
    assert "serviceKey" not in persisted
    assert SECRET not in persisted

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 2
    assert len(snapshots) == 2
    assert all("serviceKey=" not in item.url and SECRET not in item.url for item in sources)
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])


def test_unchanged_rerun_is_noop_and_changed_result_creates_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-rerun.db")
    api = three_winner_api()
    enumerator = LocalElectionWinnerEnumerator(api.connector(), repository)
    first = enumerator.enumerate()
    second = enumerator.enumerate()
    api.pages[1][0] = winner_row("C-001", "가당선", votes="12,999")
    changed = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(
        LocalElectionWinnerEnumerator.FEEDER, SCOPE, "C-001"
    )
    assert len(versions) == 2
    assert {item.normalized["votes"] for item in versions} == {12345, 12999}
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_retains_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-resume.db")
    api = three_winner_api()
    api.fail_pages.add(2)
    enumerator = LocalElectionWinnerEnumerator(api.connector(), repository)

    with pytest.raises(NecApiError):
        enumerator.enumerate()

    partial = repository.source_runs(LocalElectionWinnerEnumerator.FEEDER, SCOPE)[-1]
    checkpoint = repository.source_checkpoint(LocalElectionWinnerEnumerator.FEEDER, SCOPE)
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert partial.error_summary == "NEC winner enumeration did not complete"
    assert SECRET not in repr(partial.model_dump(mode="json"))
    assert checkpoint is not None and checkpoint.cursor == "1"

    api.fail_pages.clear()
    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.pages_committed == 1
    assert resumed.unique_records == 3
    assert api.calls[-1] == 2


def test_checkpoint_does_not_advance_when_page_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "nec-atomic.db")
    api = three_winner_api()
    enumerator = LocalElectionWinnerEnumerator(api.connector(), repository)
    original = repository.commit_source_page
    calls = 0

    def fail_second_page(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic NEC persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_page)
    with pytest.raises(RuntimeError, match="synthetic NEC"):
        enumerator.enumerate()

    checkpoint = repository.source_checkpoint(LocalElectionWinnerEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert len(
        repository.feeder_observations(LocalElectionWinnerEnumerator.FEEDER, SCOPE)
    ) == 2


@pytest.mark.parametrize(
    ("totals", "provider_pages", "provider_sizes", "message"),
    [
        ({1: 3, 2: 4}, {}, {}, "total count changed"),
        ({}, {1: 2}, {}, "provider page is inconsistent"),
        ({}, {}, {1: 1}, "provider page size is inconsistent"),
    ],
)
def test_coverage_metadata_change_fails_closed(
    tmp_path: Path,
    totals: dict[int, int],
    provider_pages: dict[int, int],
    provider_sizes: dict[int, int],
    message: str,
) -> None:
    repository = migrated_repository(tmp_path / f"nec-{message[:5]}.db")
    api = three_winner_api()
    api.totals = totals
    api.provider_pages = provider_pages
    api.provider_sizes = provider_sizes

    with pytest.raises(NecWinnerCoverageError, match=message):
        LocalElectionWinnerEnumerator(api.connector(), repository).enumerate()


@pytest.mark.parametrize(
    ("second_row", "message"),
    [
        (winner_row("C-001", "가당선"), "duplicate NEC huboid"),
        (
            winner_row("C-001", "가당선", party="충돌정당"),
            "conflicting NEC huboid",
        ),
    ],
)
def test_duplicate_or_conflicting_huboid_fails_closed(
    tmp_path: Path, second_row: dict[str, str], message: str
) -> None:
    repository = migrated_repository(tmp_path / f"nec-{message[:4]}.db")
    api = WinnerApi(
        {1: [winner_row("C-001", "가당선")], 2: [second_row]}
    )

    with pytest.raises(NecWinnerCoverageError, match=message):
        LocalElectionWinnerEnumerator(api.connector(page_size=1), repository).enumerate()

    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_policy_and_filter_denial_happen_before_network_or_run(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-blocked.db")
    api = three_winner_api()
    policy = nec_local_election_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        LocalElectionWinnerEnumerator(api.connector(), repository, policy).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []

    filtered = NecWinnerConnector(
        election_id="20260603",
        election_type=4,
        api_key=SECRET,
        province_name="경기도",
        transport=httpx.MockTransport(api.handle),
    )
    with pytest.raises(NecWinnerCoverageError, match="must be unfiltered"):
        LocalElectionWinnerEnumerator(filtered, repository).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []


def test_zero_result_scope_is_committed_as_complete_audit(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-empty.db")
    api = WinnerApi({})

    result = LocalElectionWinnerEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 1
    assert result.unique_records == 0
    assert api.calls == [1]
    checkpoint = repository.source_checkpoint(LocalElectionWinnerEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.metadata["total_count"] == 0
    assert checkpoint.metadata["expected_pages"] == 1
