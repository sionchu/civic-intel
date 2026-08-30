from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly import (
    AssemblyApiError,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.assembly_roster import AssemblyCoverageError, AssemblyRosterEnumerator

SECRET = "batch-secret-must-not-persist"


def member_row(code: str, name: str, *, party: str = "테스트정당") -> dict[str, str]:
    return {
        "MONA_CD": code,
        "HG_NM": name,
        "HJ_NM": f"{name}漢字",
        "ENG_NM": f"{name} English",
        "BTH_DATE": "19700102",
        "POLY_NM": party,
        "ORIG_NM": "서울 테스트구",
        "REELE_GBN_NM": "재선",
        "ELECT_GBN_NM": "지역구",
        "CMITS": "테스트위원회",
        "TEL_NO": "02-1111-2222",
        "E_MAIL": "do-not-store@example.invalid",
        "KEY": SECRET,
    }


class RosterApi:
    def __init__(
        self,
        pages: dict[int, list[dict[str, str]]],
        *,
        totals: dict[int, int] | None = None,
    ) -> None:
        self.pages = pages
        self.totals = totals or {}
        self.fail_pages: set[int] = set()
        self.calls: list[int] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        page = int(request.url.params["pIndex"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.pages.get(page, [])
        total = self.totals.get(page, sum(len(items) for items in self.pages.values()))
        payload = {
            OpenAssemblyMemberConnector.API_CODE: [
                {
                    "head": [
                        {"list_total_count": total},
                        {"RESULT": {"CODE": "INFO-000", "MESSAGE": "정상"}},
                    ]
                },
                {"row": rows},
            ]
        }
        return httpx.Response(200, json=payload)

    def connector(self, *, page_size: int = 2) -> OpenAssemblyMemberConnector:
        return OpenAssemblyMemberConnector(
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


def three_member_api() -> RosterApi:
    return RosterApi(
        {
            1: [member_row("M-001", "가회원"), member_row("M-002", "나회원")],
            2: [member_row("M-003", "다회원")],
        }
    )


def test_full_enumeration_persists_complete_privacy_minimized_roster(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "batch.db")
    api = three_member_api()

    result = AssemblyRosterEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3
    assert result.run.observations_unchanged == 0
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["list_total_count"] == 3
    assert checkpoint.metadata["expected_pages"] == 2

    observations = repository.feeder_observations(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert len(observations) == 3
    persisted = repr([item.model_dump(mode="json") for item in observations])
    assert "TEL_NO" not in persisted
    assert "E_MAIL" not in persisted
    assert "do-not-store@example.invalid" not in persisted
    assert SECRET not in persisted
    assert observations[0].identity_hints["external_ids"] == {
        "assembly_mona_cd": observations[0].provider_record_key
    }

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 2
    assert len(snapshots) == 2
    assert all("KEY=" not in item.url and SECRET not in item.url for item in sources)
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])


def test_unchanged_full_rerun_is_observation_noop(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "rerun.db")
    api = three_member_api()
    enumerator = AssemblyRosterEnumerator(api.connector(), repository)
    first = enumerator.enumerate()
    second = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.status == SourceRunStatus.SUCCESS
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert len(
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    ) == 3


def test_changed_provider_record_creates_immutable_observation_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "changed.db")
    api = three_member_api()
    enumerator = AssemblyRosterEnumerator(api.connector(), repository)
    enumerator.enumerate()
    api.pages[1][0] = member_row("M-001", "가회원", party="변경정당")

    changed = enumerator.enumerate()

    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(
        AssemblyRosterEnumerator.FEEDER,
        AssemblyRosterEnumerator.SCOPE_KEY,
        "M-001",
    )
    assert len(versions) == 2
    assert {item.normalized["party"] for item in versions} == {"테스트정당", "변경정당"}
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_keeps_committed_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "resume.db")
    api = three_member_api()
    api.fail_pages.add(2)
    enumerator = AssemblyRosterEnumerator(api.connector(), repository)

    with pytest.raises(AssemblyApiError):
        enumerator.enumerate()

    partial = repository.source_runs(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )[-1]
    checkpoint = repository.source_checkpoint(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert partial.error_summary == "Assembly enumeration did not complete"
    assert SECRET not in repr(partial.model_dump(mode="json"))
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert len(
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    ) == 2

    api.fail_pages.clear()
    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.pages_committed == 1
    assert resumed.unique_records == 3
    assert api.calls[-1] == 2
    assert len(
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    ) == 3


def test_checkpoint_does_not_advance_when_page_persistence_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = migrated_repository(tmp_path / "atomic.db")
    api = three_member_api()
    enumerator = AssemblyRosterEnumerator(api.connector(), repository)
    original = repository.commit_source_page
    calls = 0

    def fail_second_page(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_page)
    with pytest.raises(RuntimeError, match="synthetic persistence"):
        enumerator.enumerate()

    checkpoint = repository.source_checkpoint(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert len(
        repository.feeder_observations(
            AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
        )
    ) == 2


def test_total_count_change_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "total.db")
    api = three_member_api()
    api.totals = {1: 3, 2: 4}

    with pytest.raises(AssemblyCoverageError, match="total count changed"):
        AssemblyRosterEnumerator(api.connector(), repository).enumerate()

    run = repository.source_runs(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )[-1]
    assert run.status == SourceRunStatus.PARTIAL
    assert run.checkpoint_after == "1"


@pytest.mark.parametrize(
    ("second_row", "message"),
    [
        (member_row("M-001", "가회원"), "duplicate MONA_CD"),
        (member_row("M-001", "가회원", party="충돌정당"), "conflicting MONA_CD"),
    ],
)
def test_duplicate_or_conflicting_provider_key_fails_closed(
    tmp_path: Path, second_row: dict[str, str], message: str
) -> None:
    repository = migrated_repository(tmp_path / f"{message[:3]}.db")
    api = RosterApi({1: [member_row("M-001", "가회원")], 2: [second_row]})

    with pytest.raises(AssemblyCoverageError, match=message):
        AssemblyRosterEnumerator(api.connector(page_size=1), repository).enumerate()

    run = repository.source_runs(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    )[-1]
    assert run.status == SourceRunStatus.PARTIAL
    assert run.checkpoint_after == "1"


def test_policy_denial_blocks_before_network_or_run_receipt(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "blocked.db")
    api = three_member_api()
    policy = national_assembly_member_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )

    with pytest.raises(PolicyDenied):
        AssemblyRosterEnumerator(api.connector(), repository, policy).enumerate()

    assert api.calls == []
    assert repository.source_runs(
        AssemblyRosterEnumerator.FEEDER, AssemblyRosterEnumerator.SCOPE_KEY
    ) == []
