from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.nec_local_elections import (
    NecApiError,
    NecCandidateConnector,
    nec_local_election_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers import local_elections
from workers.local_elections import (
    LocalElectionCandidateEnumerator,
    NecCandidateCoverageError,
)

SECRET = "nec-candidate-secret-must-not-persist"
SCOPE = "20260603:4"


def candidate_row(
    candidate_id: str,
    name: str,
    *,
    party: str = "테스트당",
    status: str | None = "등록",
    election_id: str = "20260603",
    election_type: str = "4",
) -> dict[str, str]:
    row = {
        "sgId": election_id,
        "sgTypecode": election_type,
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
        "serviceKey": SECRET,
    }
    if status is not None:
        row["status"] = status
    return row


class CandidateApi:
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
        assert "jdName" not in request.url.params
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

    def connector(self, *, page_size: int = 2) -> NecCandidateConnector:
        return NecCandidateConnector(
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


def three_candidate_api() -> CandidateApi:
    return CandidateApi(
        {
            1: [candidate_row("C-001", "가후보"), candidate_row("C-002", "나후보")],
            2: [candidate_row("C-003", "다후보")],
        }
    )


def test_full_candidate_enumeration_is_complete_minimized_and_semantic(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "nec-candidates.db")
    api = three_candidate_api()

    result = LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["expected_pages"] == 2
    assert checkpoint.metadata["total_count"] == 3

    observations = repository.feeder_observations(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
    assert len(observations) == 3
    first = observations[0]
    assert first.semantic_scope == "local_election_candidacy"
    assert first.identity_hints["external_ids"] == {"nec_huboid": "C-001"}
    assert first.identity_hints["canonical_name"] == "가후보"
    assert first.normalized["registration_status"] == "등록"
    assert first.normalized["submission_semantics"] == "candidate_submitted_election_disclosure"
    assert "outcome" not in first.normalized
    assert first.provider_observed_at is not None
    assert first.provider_observed_at.date().isoformat() == "2026-06-03"
    persisted = repr([item.model_dump(mode="json") for item in observations])
    for forbidden in (
        "addr",
        "address",
        "비공개동",
        "gender",
        "age",
        "jobId",
        "eduId",
        "serviceKey",
        SECRET,
    ):
        assert forbidden.casefold() not in persisted.casefold()

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 2
    assert len(snapshots) == 2
    assert all("serviceKey=" not in item.url and SECRET not in item.url for item in sources)
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])


def test_unchanged_rerun_is_noop_and_registration_change_creates_version(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "nec-candidate-rerun.db")
    api = three_candidate_api()
    enumerator = LocalElectionCandidateEnumerator(api.connector(), repository)

    first = enumerator.enumerate()
    second = enumerator.enumerate()
    api.pages[1][0] = candidate_row("C-001", "가후보", status="사퇴")
    changed = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(
        LocalElectionCandidateEnumerator.FEEDER, SCOPE, "C-001"
    )
    assert len(versions) == 2
    assert {item.normalized["registration_status"] for item in versions} == {"등록", "사퇴"}
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_retains_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-candidate-resume.db")
    api = three_candidate_api()
    api.fail_pages.add(2)
    enumerator = LocalElectionCandidateEnumerator(api.connector(), repository)

    with pytest.raises(NecApiError):
        enumerator.enumerate()

    partial = repository.source_runs(LocalElectionCandidateEnumerator.FEEDER, SCOPE)[-1]
    checkpoint = repository.source_checkpoint(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert partial.error_summary == "NEC candidate enumeration did not complete"
    assert SECRET not in repr(partial.model_dump(mode="json"))
    assert checkpoint is not None and checkpoint.cursor == "1"

    api.fail_pages.clear()
    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.pages_committed == 1
    assert resumed.unique_records == 3
    assert api.calls[-1] == 2


def test_checkpoint_does_not_advance_when_candidate_page_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "nec-candidate-atomic.db")
    api = three_candidate_api()
    enumerator = LocalElectionCandidateEnumerator(api.connector(), repository)
    original = repository.commit_source_page
    calls = 0

    def fail_second_page(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic NEC candidate persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_page)
    with pytest.raises(RuntimeError, match="synthetic NEC candidate"):
        enumerator.enumerate()

    checkpoint = repository.source_checkpoint(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert len(repository.feeder_observations(LocalElectionCandidateEnumerator.FEEDER, SCOPE)) == 2


@pytest.mark.parametrize(
    ("totals", "provider_pages", "provider_sizes", "message"),
    [
        ({1: 3, 2: 4}, {}, {}, "total count changed"),
        ({}, {1: 2}, {}, "provider page is inconsistent"),
        ({}, {}, {1: 1}, "provider page size is inconsistent"),
    ],
)
def test_candidate_coverage_metadata_change_fails_closed(
    tmp_path: Path,
    totals: dict[int, int],
    provider_pages: dict[int, int],
    provider_sizes: dict[int, int],
    message: str,
) -> None:
    repository = migrated_repository(tmp_path / f"nec-candidate-{message[:5]}.db")
    api = three_candidate_api()
    api.totals = totals
    api.provider_pages = provider_pages
    api.provider_sizes = provider_sizes

    with pytest.raises(NecCandidateCoverageError, match=message):
        LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()


def test_candidate_incomplete_page_or_wrong_scope_fails_closed(tmp_path: Path) -> None:
    incomplete_repository = migrated_repository(tmp_path / "nec-candidate-incomplete.db")
    incomplete = CandidateApi(
        {1: [candidate_row("C-001", "가후보")], 2: []},
        totals={1: 2, 2: 2},
    )
    with pytest.raises(NecCandidateCoverageError, match="page row count is incomplete"):
        LocalElectionCandidateEnumerator(
            incomplete.connector(page_size=1), incomplete_repository
        ).enumerate()

    wrong_scope_repository = migrated_repository(tmp_path / "nec-candidate-wrong-scope.db")
    wrong_scope = CandidateApi({1: [candidate_row("C-001", "가후보", election_id="20220415")]})
    with pytest.raises(NecCandidateCoverageError, match="row election id is inconsistent"):
        LocalElectionCandidateEnumerator(
            wrong_scope.connector(), wrong_scope_repository
        ).enumerate()


@pytest.mark.parametrize(
    ("second_row", "message"),
    [
        (candidate_row("C-001", "가후보"), "duplicate NEC huboid"),
        (
            candidate_row("C-001", "가후보", party="충돌정당"),
            "conflicting NEC huboid",
        ),
    ],
)
def test_duplicate_or_conflicting_candidate_huboid_fails_closed(
    tmp_path: Path, second_row: dict[str, str], message: str
) -> None:
    repository = migrated_repository(tmp_path / f"nec-candidate-{message[:4]}.db")
    api = CandidateApi({1: [candidate_row("C-001", "가후보")], 2: [second_row]})

    with pytest.raises(NecCandidateCoverageError, match=message):
        LocalElectionCandidateEnumerator(api.connector(page_size=1), repository).enumerate()

    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_candidate_policy_filter_and_required_status_fail_before_unsafe_progress(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "nec-candidate-blocked.db")
    api = three_candidate_api()
    policy = nec_local_election_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        LocalElectionCandidateEnumerator(api.connector(), repository, policy).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []

    filtered = NecCandidateConnector(
        election_id="20260603",
        election_type=4,
        api_key=SECRET,
        party="테스트당",
        transport=httpx.MockTransport(api.handle),
    )
    with pytest.raises(NecCandidateCoverageError, match="must be unfiltered"):
        LocalElectionCandidateEnumerator(filtered, repository).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []

    missing_status_repository = migrated_repository(tmp_path / "nec-candidate-status.db")
    missing_status = CandidateApi({1: [candidate_row("C-001", "가후보", status=None)]})
    with pytest.raises(NecCandidateCoverageError, match="registration status is unavailable"):
        LocalElectionCandidateEnumerator(
            missing_status.connector(), missing_status_repository
        ).enumerate()
    assert missing_status_repository.source_runs()[-1].status == SourceRunStatus.FAILED
    assert (
        missing_status_repository.source_checkpoint(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
        is None
    )


def test_zero_candidate_scope_is_committed_as_complete_audit(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "nec-candidate-empty.db")
    api = CandidateApi({})

    result = LocalElectionCandidateEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 1
    assert result.unique_records == 0
    assert api.calls == [1]
    checkpoint = repository.source_checkpoint(LocalElectionCandidateEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.metadata["total_count"] == 0
    assert checkpoint.metadata["expected_pages"] == 1


def test_cli_routes_candidate_enumeration_and_resume_without_live_fetch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    observed: dict[str, object] = {}

    class FakeCandidateEnumerator:
        def __init__(self, connector, repository) -> None:
            observed["connector"] = connector
            observed["repository"] = repository

        def enumerate(self, *, resume: bool = False):
            observed["resume"] = resume
            return SimpleNamespace(
                run=SimpleNamespace(
                    id=UUID("00000000-0000-0000-0000-000000000123"),
                    status=SourceRunStatus.SUCCESS,
                    scope_key=SCOPE,
                ),
                pages_committed=2,
                unique_records=3,
            )

    monkeypatch.setattr(
        local_elections, "LocalElectionCandidateEnumerator", FakeCandidateEnumerator
    )

    result = local_elections.main(
        [
            "--election-id",
            "20260603",
            "--type",
            "4",
            "--enumerate-candidates",
            "--resume",
            "--database-url",
            f"sqlite:///{(tmp_path / 'cli.db').as_posix()}",
        ]
    )

    assert result == 0
    assert observed["resume"] is True
    assert isinstance(observed["connector"], NecCandidateConnector)
    payload = capsys.readouterr().out
    assert '"scope_key": "20260603:4"' in payload
    assert '"unique_records": 3' in payload
