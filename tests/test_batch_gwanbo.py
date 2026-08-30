from __future__ import annotations

from datetime import date
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.gwanbo_personnel import (
    GwanboPersonnelConnector,
    GwanboPersonnelError,
    gwanbo_personnel_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import SourceCollectionMode, SourceRunStatus
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.gwanbo_personnel import GwanboCoverageError, GwanboPersonnelEnumerator

SECRET = "gwanbo-secret-must-not-persist"
DATE_FROM = date(2026, 8, 1)
DATE_TO = date(2026, 8, 31)


def notice(
    notice_id: str,
    title: str,
    *,
    institution: str = "행정안전부",
    revision_reason: str = "",
) -> tuple[str, ...]:
    return (
        notice_id,
        title,
        "2026.08.15",
        "관보 제12345호",
        "인사",
        institution,
        "국가공무원법",
        f"https://example.invalid/original/{notice_id}?token={SECRET}",
        "Y",
        revision_reason,
        f"/OpenApi/web/detail/{notice_id}",
    )


def page_html(rows: list[tuple[str, ...]], total: int) -> str:
    if not rows and total == 0:
        return """
        <li id="countArea"><span>총 건수 : 건</span></li>
        <table><tbody><tr><td colspan="5">검색결과가 존재하지 않습니다.</td></tr></tbody></table>
        """
    rendered = []
    for index, row in enumerate(rows, start=1):
        arguments = ",".join(f"'{value}'" for value in row)
        rendered.append(
            "<tr>"
            f"<td>{index}</td><td><a onclick=\"fnDetail({arguments});\">{row[1]}</a></td>"
            f"<td>{row[5]}</td><td>{row[6]}</td><td>{row[2]}</td>"
            "</tr>"
        )
    return (
        f'<li id="countArea"><span>총 건수 : {total:,}건</span></li>'
        f"<table><tbody>{''.join(rendered)}</tbody></table>"
    )


class GwanboApi:
    def __init__(
        self,
        pages: dict[int, list[tuple[str, ...]]],
        *,
        totals: dict[int, int] | None = None,
    ) -> None:
        self.pages = pages
        self.totals = totals or {}
        self.fail_pages: set[int] = set()
        self.calls: list[int] = []
        self.request_bodies: list[dict[str, list[str]]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert str(request.url) == GwanboPersonnelConnector.AJAX_URL
        form = parse_qs(request.content.decode(), keep_blank_values=True)
        self.request_bodies.append(form)
        assert form["themaSe"] == ["06"]
        assert form["reqFrom"] == ["2026.08.01"]
        assert form["reqTo"] == ["2026.08.31"]
        assert set(form) == {
            "rowPerPage",
            "currentPage",
            "themaSe",
            "reqFrom",
            "reqTo",
            "search",
            "pblcnSearch",
            "lawNmSearch",
        }
        page_index = int(form["currentPage"][0])
        self.calls.append(page_index)
        if page_index in self.fail_pages:
            return httpx.Response(503, text=f"provider failure {SECRET}")
        rows = self.pages.get(page_index, [])
        total = self.totals.get(page_index, sum(len(items) for items in self.pages.values()))
        return httpx.Response(200, text=page_html(rows, total))

    def connector(self, *, page_size: int = 2) -> GwanboPersonnelConnector:
        return GwanboPersonnelConnector(
            date_from=DATE_FROM,
            date_to=DATE_TO,
            page_size=page_size,
            transport=httpx.MockTransport(self.handle),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def three_notice_api() -> GwanboApi:
    return GwanboApi(
        {
            1: [notice("G-001", "고위공무원 인사발령"), notice("G-002", "정부 인사발령")],
            2: [notice("G-003", "외무공무원 인사발령", institution="외교부")],
        }
    )


def test_connector_uses_official_post_contract_without_authentication() -> None:
    api = GwanboApi({1: [notice("G-001", "인사발령")]})
    connector = api.connector()

    document = connector.fetch(connector.discover()[0])
    records = connector.parse_notices(document)

    assert document.metadata["source_contract"] == "gwanbo_personnel_notice_list"
    assert document.metadata["list_total_count"] == "1"
    assert records[0].notice_id == "G-001"
    assert records[0].title == "인사발령"
    assert records[0].publication_date == date(2026, 8, 15)
    assert records[0].publication_institution == "행정안전부"
    assert "auth" not in repr(api.request_bodies).casefold()
    assert SECRET in document.body


def test_full_enumeration_is_complete_minimized_and_person_neutral(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "gwanbo.db")
    api = three_notice_api()

    result = GwanboPersonnelEnumerator(api.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 2
    assert result.unique_records == 3
    assert result.run.records_seen == 3
    assert result.run.observations_created == 3
    assert api.calls == [1, 2]
    checkpoint = repository.source_checkpoint(
        GwanboPersonnelEnumerator.FEEDER, "2026-08-01:2026-08-31"
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["expected_pages"] == 2
    assert checkpoint.metadata["list_total_count"] == 3

    observations = repository.feeder_observations(
        GwanboPersonnelEnumerator.FEEDER, "2026-08-01:2026-08-31"
    )
    assert len(observations) == 3
    assert all(item.identity_hints == {} for item in observations)
    persisted = repr([item.model_dump(mode="json") for item in observations])
    assert "canonical_name" not in persisted
    assert "person_name" not in persisted
    assert "orgnflPathUrlAddr" not in persisted
    assert "crtnYnPrnt" not in persisted
    assert SECRET not in persisted

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 2
    assert len(snapshots) == 2
    assert all(item.fulltext is None for item in snapshots)
    assert SECRET not in repr([item.metadata_json for item in snapshots])
    assert all("token=" not in item.url for item in sources)


def test_rerun_is_noop_and_changed_notice_creates_version(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "rerun.db")
    api = three_notice_api()
    enumerator = GwanboPersonnelEnumerator(api.connector(), repository)
    first = enumerator.enumerate()
    second = enumerator.enumerate()
    api.pages[1][0] = notice("G-001", "고위공무원 인사발령 정정", revision_reason="정정")
    changed = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    versions = repository.feeder_observations(
        GwanboPersonnelEnumerator.FEEDER,
        "2026-08-01:2026-08-31",
        "G-001",
    )
    assert len(versions) == 2
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_retains_checkpoint_and_resume_completes(tmp_path: Path) -> None:
    repository = migrated_repository(tmp_path / "resume.db")
    api = three_notice_api()
    api.fail_pages.add(2)
    enumerator = GwanboPersonnelEnumerator(api.connector(), repository)

    with pytest.raises(GwanboPersonnelError):
        enumerator.enumerate()

    partial = repository.source_runs(
        GwanboPersonnelEnumerator.FEEDER, "2026-08-01:2026-08-31"
    )[-1]
    assert partial.status == SourceRunStatus.PARTIAL
    assert partial.checkpoint_after == "1"
    assert SECRET not in repr(partial.model_dump(mode="json"))

    api.fail_pages.clear()
    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.pages_committed == 1
    assert resumed.unique_records == 3
    assert api.calls[-1] == 2


def test_total_change_and_duplicate_notice_fail_closed(tmp_path: Path) -> None:
    total_repository = migrated_repository(tmp_path / "total.db")
    changing = three_notice_api()
    changing.totals = {1: 3, 2: 4}
    with pytest.raises(GwanboCoverageError, match="total count changed"):
        GwanboPersonnelEnumerator(changing.connector(), total_repository).enumerate()
    assert total_repository.source_runs()[-1].status == SourceRunStatus.PARTIAL

    duplicate_repository = migrated_repository(tmp_path / "duplicate.db")
    duplicate = GwanboApi(
        {1: [notice("G-001", "인사발령")], 2: [notice("G-001", "인사발령")]}
    )
    with pytest.raises(GwanboCoverageError, match="duplicate Gwanbo notice id"):
        GwanboPersonnelEnumerator(
            duplicate.connector(page_size=1), duplicate_repository
        ).enumerate()
    assert duplicate_repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_empty_official_shape_is_audited_and_policy_denial_precedes_network(
    tmp_path: Path,
) -> None:
    repository = migrated_repository(tmp_path / "empty.db")
    empty = GwanboApi({})
    result = GwanboPersonnelEnumerator(empty.connector(), repository).enumerate()
    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.pages_committed == 1
    assert result.unique_records == 0
    assert empty.calls == [1]

    blocked_repository = migrated_repository(tmp_path / "blocked.db")
    blocked_api = GwanboApi({})
    policy = gwanbo_personnel_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        GwanboPersonnelEnumerator(
            blocked_api.connector(), blocked_repository, policy
        ).enumerate()
    assert blocked_api.calls == []
    assert blocked_repository.source_runs() == []


def test_policy_blocks_unlicensed_downstream_uses_and_window_is_bounded() -> None:
    policy = gwanbo_personnel_policy()
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is False
    assert policy.can_commercialize is False
    assert policy.license is None

    with pytest.raises(ValueError, match="three years"):
        GwanboPersonnelConnector(
            date_from=date(2020, 1, 1),
            date_to=date(2026, 1, 1),
        )
