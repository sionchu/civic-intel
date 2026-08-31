from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly import AssemblyApiError
from packages.connectors.open_assembly_bills import (
    OpenAssemblyBillConnector,
    national_assembly_bill_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.legislative_activity import (
    AssemblyBillCoverageError,
    AssemblyBillParticipationEnumerator,
)

SECRET = "assembly-bill-secret-must-not-persist"
SCOPE = "assembly_age:22"


def bill_row(
    bill_id: str,
    bill_name: str,
    *,
    age: str = "22",
    process_result: str = "계류",
    lead_codes: str = "M001",
    co_codes: str = "M002;M003",
) -> dict[str, str]:
    return {
        "BILL_ID": bill_id,
        "BILL_NO": f"220{bill_id[-1]}001",
        "BILL_NAME": bill_name,
        "COMMITTEE": "테스트위원회",
        "COMMITTEE_ID": "CMIT-001",
        "PROPOSE_DT": "2026-01-02",
        "PROC_RESULT": process_result,
        "AGE": age,
        "PROPOSER": "비저장대표의원 등 3인",
        "RST_PROPOSER": "비저장대표",
        "PUBL_PROPOSER": "비저장공동1,비저장공동2",
        "RST_MONA_CD": lead_codes,
        "PUBL_MONA_CD": co_codes,
        "DETAIL_LINK": (
            f"https://open.assembly.go.kr/bill/{bill_id}?KEY={SECRET}&billId={bill_id}"
        ),
        "KEY": SECRET,
    }


class BillApi:
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
        assert request.method == "GET"
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["AGE"] == "22"
        for filter_name in (
            "BILL_ID",
            "BILL_NO",
            "BILL_NAME",
            "COMMITTEE",
            "COMMITTEE_ID",
            "PROC_RESULT",
            "PROPOSER",
        ):
            assert filter_name not in request.url.params
        page = int(request.url.params["pIndex"])
        page_size = int(request.url.params["pSize"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.pages.get(page, [])
        total = self.totals.get(page, sum(len(items) for items in self.pages.values()))
        result_code = "INFO-200" if total == 0 else "INFO-000"
        payload = {
            OpenAssemblyBillConnector.API_CODE: [
                {
                    "head": [
                        {"list_total_count": total},
                        {"RESULT": {"CODE": result_code, "MESSAGE": "정상"}},
                    ]
                },
                {"row": rows[:page_size]},
            ]
        }
        return httpx.Response(200, json=payload)

    def connector(self, *, page_size: int = 2) -> OpenAssemblyBillConnector:
        return OpenAssemblyBillConnector(
            assembly_age=22,
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


def three_bill_api() -> BillApi:
    return BillApi(
        {
            1: [bill_row("B1", "첫 번째 법률안"), bill_row("B2", "두 번째 법률안")],
            2: [bill_row("B3", "세 번째 법률안", process_result="원안가결")],
        }
    )


def test_full_term_enumeration_is_complete_code_first_and_minimized(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills.db")
    api = three_bill_api()

    result = AssemblyBillParticipationEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["expected_pages"] == 2
    assert checkpoint.metadata["list_total_count"] == 3
    assert checkpoint.metadata["assembly_age"] == 22

    observations = repository.feeder_observations(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)
    assert len(observations) == 3
    first = observations[0]
    assert first.provider_record_key == "B1"
    assert first.identity_hints["record_kind"] == "multi_person_legislative_event"
    assert first.identity_hints["participants"] == [
        {
            "external_id_namespace": "assembly_mona_cd",
            "external_id": "M001",
            "role": "REPRESENTATIVE_PROPOSER",
        },
        {
            "external_id_namespace": "assembly_mona_cd",
            "external_id": "M002",
            "role": "CO_PROPOSER",
        },
        {
            "external_id_namespace": "assembly_mona_cd",
            "external_id": "M003",
            "role": "CO_PROPOSER",
        },
    ]
    assert first.provider_observed_at is not None
    assert first.provider_observed_at.date().isoformat() == "2026-01-02"
    assert first.normalized["detail_url"] == ("https://open.assembly.go.kr/bill/B1?billId=B1")
    assert "representative_proposers" not in first.normalized
    assert "co_proposers" not in first.normalized
    assert "proposer_summary" not in first.normalized
    persisted = repr([item.model_dump(mode="json") for item in observations])
    assert "비저장대표" not in persisted
    assert "비저장공동" not in persisted
    assert SECRET not in persisted

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 2
    assert len(snapshots) == 2
    assert all("KEY=" not in item.url and SECRET not in item.url for item in sources)
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])


def test_unchanged_rerun_is_noop_and_changed_bill_creates_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-rerun.db")
    api = three_bill_api()
    enumerator = AssemblyBillParticipationEnumerator(api.connector(), repository)

    first = enumerator.enumerate()
    second = enumerator.enumerate()
    api.pages[1][0] = bill_row("B1", "첫 번째 법률안", process_result="수정가결")
    changed = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(
        AssemblyBillParticipationEnumerator.FEEDER, SCOPE, "B1"
    )
    assert len(versions) == 2
    assert {item.normalized["process_result"] for item in versions} == {"계류", "수정가결"}
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_retains_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-resume.db")
    api = three_bill_api()
    api.fail_pages.add(2)
    enumerator = AssemblyBillParticipationEnumerator(api.connector(), repository)

    with pytest.raises(AssemblyApiError):
        enumerator.enumerate()

    partial = repository.source_runs(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)[-1]
    checkpoint = repository.source_checkpoint(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert partial.error_summary == "Assembly bill participation enumeration did not complete"
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
    repository = migrated_repository(tmp_path / "assembly-bills-atomic.db")
    api = three_bill_api()
    enumerator = AssemblyBillParticipationEnumerator(api.connector(), repository)
    original = repository.commit_source_page
    calls = 0

    def fail_second_page(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic bill persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_page)
    with pytest.raises(RuntimeError, match="synthetic bill"):
        enumerator.enumerate()

    checkpoint = repository.source_checkpoint(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None and checkpoint.cursor == "1"
    assert (
        len(repository.feeder_observations(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)) == 2
    )


@pytest.mark.parametrize(
    ("totals", "max_pages", "message"),
    [
        ({1: 3, 2: 4}, 100, "total count changed"),
        ({1: 3}, 1, "expected pages exceed"),
    ],
)
def test_total_or_expected_page_change_fails_closed(
    tmp_path: Path,
    totals: dict[int, int],
    max_pages: int,
    message: str,
) -> None:
    repository = migrated_repository(tmp_path / f"assembly-bills-{max_pages}.db")
    api = three_bill_api()
    api.totals = totals

    with pytest.raises(AssemblyBillCoverageError, match=message):
        AssemblyBillParticipationEnumerator(
            api.connector(), repository, max_pages=max_pages
        ).enumerate()


def test_incomplete_page_row_count_fails_closed_after_committed_page(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-row-count.db")
    api = three_bill_api()
    api.pages[2] = []
    api.totals = {1: 3, 2: 3}

    with pytest.raises(AssemblyBillCoverageError, match="row count is incomplete"):
        AssemblyBillParticipationEnumerator(api.connector(), repository).enumerate()

    run = repository.source_runs(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)[-1]
    assert run.status == SourceRunStatus.PARTIAL
    assert run.checkpoint_after == "1"


@pytest.mark.parametrize(
    ("second_row", "message"),
    [
        (bill_row("B1", "첫 번째 법률안"), "duplicate page content"),
        (
            bill_row("B1", "충돌하는 법률안"),
            "conflicting BILL_ID",
        ),
    ],
)
def test_duplicate_or_conflicting_bill_id_fails_closed(
    tmp_path: Path,
    second_row: dict[str, str],
    message: str,
) -> None:
    repository = migrated_repository(tmp_path / f"assembly-bills-{message[:4]}.db")
    api = BillApi({1: [bill_row("B1", "첫 번째 법률안")], 2: [second_row]})

    with pytest.raises(AssemblyBillCoverageError, match=message):
        AssemblyBillParticipationEnumerator(api.connector(page_size=1), repository).enumerate()

    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_duplicate_bill_id_on_nonidentical_page_fails_closed(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-duplicate-id.db")
    api = BillApi(
        {
            1: [bill_row("B1", "첫 번째 법률안"), bill_row("B2", "두 번째 법률안")],
            2: [bill_row("B1", "첫 번째 법률안"), bill_row("B3", "세 번째 법률안")],
        }
    )

    with pytest.raises(AssemblyBillCoverageError, match="duplicate BILL_ID"):
        AssemblyBillParticipationEnumerator(api.connector(), repository).enumerate()

    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (bill_row("B1", "잘못된 대수", age="21"), "row Assembly age"),
        (
            {
                key: value
                for key, value in bill_row("B1", "코드 누락").items()
                if key != "PUBL_MONA_CD"
            },
            "complete proposer code fields",
        ),
        (
            bill_row("B1", "코드 구분자 오류", co_codes="M002,M003"),
            "complete proposer code fields",
        ),
    ],
)
def test_wrong_term_or_incomplete_role_codes_fail_before_commit(
    tmp_path: Path,
    row: dict[str, str],
    message: str,
) -> None:
    repository = migrated_repository(tmp_path / f"assembly-bills-{message[:3]}.db")
    api = BillApi({1: [row]})

    with pytest.raises(AssemblyBillCoverageError, match=message):
        AssemblyBillParticipationEnumerator(api.connector(), repository).enumerate()

    assert repository.source_runs()[-1].status == SourceRunStatus.FAILED
    assert repository.source_checkpoint(AssemblyBillParticipationEnumerator.FEEDER, SCOPE) is None


def test_policy_and_scope_denial_happen_before_network_or_run(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-blocked.db")
    api = three_bill_api()
    policy = national_assembly_bill_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        AssemblyBillParticipationEnumerator(api.connector(), repository, policy).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []

    filtered = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        proposer="비저장대표",
        transport=httpx.MockTransport(api.handle),
    )
    with pytest.raises(AssemblyBillCoverageError, match="must be unfiltered"):
        AssemblyBillParticipationEnumerator(filtered, repository).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []

    page_two = OpenAssemblyBillConnector(
        assembly_age=22,
        api_key=SECRET,
        page_index=2,
        transport=httpx.MockTransport(api.handle),
    )
    with pytest.raises(AssemblyBillCoverageError, match="must start at page 1"):
        AssemblyBillParticipationEnumerator(page_two, repository).enumerate()
    assert api.calls == []
    assert repository.source_runs() == []


def test_zero_result_term_is_committed_as_complete_audit(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "assembly-bills-empty.db")
    api = BillApi({})

    result = AssemblyBillParticipationEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 1
    assert result.unique_records == 0
    assert api.calls == [1]
    checkpoint = repository.source_checkpoint(AssemblyBillParticipationEnumerator.FEEDER, SCOPE)
    assert checkpoint is not None
    assert checkpoint.metadata["list_total_count"] == 0
    assert checkpoint.metadata["expected_pages"] == 1
