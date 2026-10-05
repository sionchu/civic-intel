from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_assembly_subcommittee import (
    OpenAssemblySubcommitteeReviewConnector,
    national_assembly_subcommittee_policy,
)
from packages.domain.db import ClaimRow, FeederObservationRow, PersonRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.assembly_subcommittee_review_enumeration import (
    AssemblySubcommitteeReviewCoverageError,
    AssemblySubcommitteeReviewEnumerator,
)

SECRET = "subcommittee-l3-secret-must-not-persist"
API = OpenAssemblySubcommitteeReviewConnector.API_CODE


def row(
    bill: str,
    no: str,
    *,
    committee: str = "C1",
    committee_name: str = "위원회",
    subcommittee: str | None = "법안심사소위원회",
    referral: str = "2026-01-01",
    present_session: str | None = "430",
    present_degree: str | None = "1",
    present: str | None = "2026-01-10",
    process_session: str | None = None,
    process_degree: str | None = None,
    process: str | None = None,
    result: str | None = None,
    direct: str = "N",
    note: str | None = None,
) -> dict[str, object]:
    return {
        "AGE": "22",
        "BILL_NO": no,
        "BILL_ID": bill,
        "COMMITTEE_ID": committee,
        "COMMITTEE_NAME": committee_name,
        "SUB_COMMITTEE_NAME": subcommittee,
        "PRESENT_SESSION": present_session,
        "PRESENT_CHA": present_degree,
        "PROC_SESSION": process_session,
        "PROC_CHA": process_degree,
        "SUBMIT_DT": referral,
        "PRESENT_DT": present,
        "PROC_DT": process,
        "PROC_RESULT_CD": result,
        "ENROLL_TYPE": direct,
        "CONF_BIGO": note,
        "KEY": SECRET,
    }


def envelope(rows: list[dict], total: int) -> dict:
    return {
        API: [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": "INFO-000", "MESSAGE": f"provider {SECRET}"}},
                ]
            },
            {"row": rows},
        ]
    }


class ReviewApi:
    def __init__(self) -> None:
        b2 = row("B2", "2200002", present="2026-01-12")
        self.rows = [
            row("B0", "2200000"),
            row("B1", "2200001", present="2026-01-11"),
            row(
                "B1",
                "2200001",
                committee="C2",
                committee_name="다른위원회",
                subcommittee=None,
                referral="2026-02-01",
                present_session=None,
                present_degree=None,
                present=None,
            ),
            b2,
            dict(b2),
            row("B3", "2200003", process="2026-02-01", result="대안반영폐기"),
        ]
        self.total_by_page: dict[int, int] = {}
        self.fail_pages: set[int] = set()
        self.truncate_pages: set[int] = set()
        self.calls: list[int] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.params["AGE"] == "22"
        assert "BILL_ID" not in request.url.params
        page = int(request.url.params["pIndex"])
        size = int(request.url.params["pSize"])
        self.calls.append(page)
        if page in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        chunk = self.rows[(page - 1) * size : page * size]
        if page in self.truncate_pages and chunk:
            chunk = chunk[:-1]
        total = self.total_by_page.get(page, len(self.rows))
        return httpx.Response(200, json=envelope(chunk, total))

    def connector(self, *, page_size: int = 2) -> OpenAssemblySubcommitteeReviewConnector:
        return OpenAssemblySubcommitteeReviewConnector(
            assembly_age=22,
            api_key=SECRET,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def repository(path: Path) -> SqlAlchemyRepository:
    url = f"sqlite:///{path.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(url)


def observations(repo: SqlAlchemyRepository) -> dict[str, list[FeederObservationRow]]:
    with repo.sessions() as session:
        rows = session.scalars(
            select(FeederObservationRow)
            .where(
                FeederObservationRow.feeder
                == AssemblySubcommitteeReviewEnumerator.FEEDER
            )
            .order_by(FeederObservationRow.provider_record_key, FeederObservationRow.recorded_at)
        ).all()
    grouped: dict[str, list[FeederObservationRow]] = {}
    for item in rows:
        grouped.setdefault(item.provider_record_key, []).append(item)
    return grouped


def enumerator(
    api: ReviewApi,
    repo: SqlAlchemyRepository,
    *,
    page_size: int = 2,
    **kwargs,
) -> AssemblySubcommitteeReviewEnumerator:
    return AssemblySubcommitteeReviewEnumerator(
        api.connector(page_size=page_size),
        repo,
        **kwargs,
    )


def test_full_enumeration_aggregates_one_packet_per_bill_and_collapses_exact_duplicates(
    tmp_path: Path,
) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "review.db")

    result = enumerator(api, repo).enumerate()

    assert result.run.status is SourceRunStatus.SUCCESS
    assert result.complete is True
    assert result.provider_row_count == 6
    assert result.packet_count == 4
    assert result.pages_committed_total == 3
    assert result.exact_duplicate_surplus_rows == 1
    assert result.run.observations_created == 4

    grouped = observations(repo)
    assert sorted(grouped) == ["B0", "B1", "B2", "B3"]
    b1 = grouped["B1"][0]
    assert b1.identity_hints_json == {}
    assert b1.normalized_json["bill_no"] == "2200001"
    assert b1.normalized_json["provider_row_total"] == 2
    assert b1.normalized_json["distinct_review_rows"] == 2
    assert b1.normalized_json["duplicate_provider_rows"] == 0
    assert b1.normalized_json["source_pages"] == [1, 2]
    assert b1.normalized_json["source_page_count"] == 2
    assert len(b1.normalized_json["reviews"]) == 2

    b2 = grouped["B2"][0]
    assert b2.normalized_json["provider_row_total"] == 2
    assert b2.normalized_json["distinct_review_rows"] == 1
    assert b2.normalized_json["duplicate_provider_rows"] == 1
    assert b2.normalized_json["source_pages"] == [2, 3]
    assert b2.normalized_json["source_page_count"] == 2
    assert b2.normalized_json["reviews"][0]["provider_row_count"] == 2

    with repo.sessions() as session:
        snapshots = {
            item.id: item
            for item in session.scalars(select(SourceSnapshotRow)).all()
        }
        assert session.scalars(select(PersonRow)).all() == []
        assert session.scalars(select(ClaimRow)).all() == []
    # B1 spans source pages 1 and 2 and anchors to the last page.
    assert snapshots[b1.snapshot_id].metadata_json["page_index"] == "2"
    # B2 spans pages 2 and 3 and likewise anchors to page 3.
    assert snapshots[b2.snapshot_id].metadata_json["page_index"] == "3"
    persisted = repr([item.normalized_json for values in grouped.values() for item in values])
    assert SECRET not in persisted


def test_unchanged_rerun_is_noop_and_changed_bill_packet_versions(tmp_path: Path) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "rerun.db")
    enum = enumerator(api, repo)

    first = enum.enumerate()
    second = enum.enumerate()
    api.rows[-1]["PROC_RESULT_CD"] = "수정가결"
    changed = enum.enumerate()

    assert first.run.observations_created == 4
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 4
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 3
    b3 = observations(repo)["B3"]
    assert len(b3) == 2
    assert {
        item.normalized_json["reviews"][0]["process_result"]
        for item in b3
    } == {"대안반영폐기", "수정가결"}


def test_page_budget_then_resume_revalidates_full_universe(tmp_path: Path) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "resume.db")

    first = enumerator(api, repo, max_pages=1).enumerate()
    assert first.run.status is SourceRunStatus.PARTIAL
    assert first.run.error_code == "MaxPagesReached"
    assert first.pages_committed_total == 1
    checkpoint = repo.source_checkpoint(
        AssemblySubcommitteeReviewEnumerator.FEEDER,
        "assembly_age:22",
    )
    assert checkpoint is not None and checkpoint.cursor == "1"

    api.calls.clear()
    resumed = enumerator(api, repo).enumerate(resume=True)
    assert resumed.run.status is SourceRunStatus.SUCCESS
    assert resumed.complete is True
    assert resumed.pages_committed_this_run == 2
    # Resume still re-fetches the full 3-page source before committing from page 2.
    assert api.calls == [1, 2, 3]
    assert sorted(observations(repo)) == ["B0", "B1", "B2", "B3"]


def test_persistence_failure_keeps_last_checkpoint_and_resume_completes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "commit-failure.db")
    enum = enumerator(api, repo)

    original = repo.commit_source_page
    calls = 0

    def flaky_commit_source_page(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic persistence failure")
        return original(**kwargs)

    monkeypatch.setattr(repo, "commit_source_page", flaky_commit_source_page)
    with pytest.raises(RuntimeError, match="synthetic persistence failure"):
        enum.enumerate()

    checkpoint = repo.source_checkpoint(
        AssemblySubcommitteeReviewEnumerator.FEEDER,
        "assembly_age:22",
    )
    assert checkpoint is not None and checkpoint.cursor == "1"
    partial = repo.source_runs(
        AssemblySubcommitteeReviewEnumerator.FEEDER,
        "assembly_age:22",
    )[-1]
    assert partial.status is SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"

    monkeypatch.setattr(repo, "commit_source_page", original)
    api.calls.clear()
    resumed = enumerator(api, repo).enumerate(resume=True)
    assert resumed.run.status is SourceRunStatus.SUCCESS
    assert resumed.complete is True
    assert resumed.pages_committed_this_run == 2
    assert api.calls == [1, 2, 3]
    assert sorted(observations(repo)) == ["B0", "B1", "B2", "B3"]


def test_resume_fails_closed_if_universe_changes(tmp_path: Path) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "drift.db")
    enumerator(api, repo, max_pages=1).enumerate()

    api.rows[-1]["PROC_RESULT_CD"] = "수정가결"
    with pytest.raises(AssemblySubcommitteeReviewCoverageError, match="universe changed"):
        enumerator(api, repo).enumerate(resume=True)


def test_total_drift_and_incomplete_page_fail_closed(tmp_path: Path) -> None:
    api = ReviewApi()
    api.total_by_page[2] = 7
    with pytest.raises(AssemblySubcommitteeReviewCoverageError, match="total changed"):
        enumerator(api, repository(tmp_path / "total.db")).enumerate()

    api = ReviewApi()
    api.truncate_pages.add(1)
    with pytest.raises(AssemblySubcommitteeReviewCoverageError, match="row count"):
        enumerator(api, repository(tmp_path / "rows.db")).enumerate()


def test_same_bill_id_with_multiple_bill_numbers_fails_closed(tmp_path: Path) -> None:
    api = ReviewApi()
    api.rows[2]["BILL_NO"] = "2299999"
    with pytest.raises(AssemblySubcommitteeReviewCoverageError, match="multiple BILL_NO"):
        enumerator(api, repository(tmp_path / "bill-no.db")).enumerate()


def test_filtered_or_sample_connector_is_not_an_l3_universe(tmp_path: Path) -> None:
    repo = repository(tmp_path / "blocked-scope.db")
    with pytest.raises(ValueError, match="unfiltered AGE"):
        AssemblySubcommitteeReviewEnumerator(
            OpenAssemblySubcommitteeReviewConnector(
                assembly_age=22,
                api_key=SECRET,
                bill_id="B1",
            ),
            repo,
        )
    with pytest.raises(ValueError, match="sample mode"):
        AssemblySubcommitteeReviewEnumerator(
            OpenAssemblySubcommitteeReviewConnector(
                assembly_age=22,
                sample_mode=True,
                page_index=1,
                page_size=5,
            ),
            repo,
        )


def test_policy_denial_happens_before_network(tmp_path: Path) -> None:
    api = ReviewApi()
    repo = repository(tmp_path / "policy.db")
    blocked = national_assembly_subcommittee_policy().model_copy(
        update={
            "collection_mode": SourceCollectionMode.BLOCKED,
            "can_fetch": False,
        }
    )
    with pytest.raises(PolicyDenied):
        enumerator(api, repo, policy=blocked).enumerate()
    assert api.calls == []


def test_provider_failure_before_persistence_is_failed_and_secret_safe(tmp_path: Path) -> None:
    api = ReviewApi()
    api.fail_pages.add(2)
    repo = repository(tmp_path / "failure.db")
    with pytest.raises(Exception) as exc_info:
        enumerator(api, repo).enumerate()
    assert SECRET not in str(exc_info.value)
    assert (
        repo.source_checkpoint(
            AssemblySubcommitteeReviewEnumerator.FEEDER,
            "assembly_age:22",
        )
        is None
    )
