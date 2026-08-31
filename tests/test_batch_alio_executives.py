from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.alio_disclosures import (
    AlioExecutiveDisclosureConnector,
    AlioRecordError,
    alio_public_institution_policy,
)
from packages.domain.db import SourceRow, SourceSnapshotRow
from packages.domain.enums import (
    IdentityReviewStatus,
    MaterializationAction,
    MaterializationDecisionClass,
    SourceRunStatus,
)
from packages.persistence import SqlAlchemyRepository
from packages.verification.policy import PolicyDenied
from workers.public_institutions import AlioExecutiveEnumerator

STAFF_NAME = "수집금지담당자"
STAFF_PHONE = "02-9999-9999"


def executive_table(
    name: str,
    *,
    position: str = "상임기관장",
    title: str = "원장",
    career: str = "테스트부 차관",
) -> str:
    return f"""
    <table border="1">
      <tbody>
        <tr><td>직위</td><td>{position}</td><td>성명</td><td>{name}</td></tr>
        <tr><td>직책</td><td>{title}</td><td>성별</td><td>남</td></tr>
        <tr>
          <td>임기</td><td>(시작일)</td><td>2025년 01월 02일</td>
          <td>(종료일)</td><td>2028년 01월 01일</td>
        </tr>
        <tr><td>주요경력</td><td>{career}<br/>테스트청장</td></tr>
        <tr><td>선임절차</td><td>임원추천위원회 추천 후 임명</td></tr>
        <tr><td>선임절차규정</td><td>기관 정관</td></tr>
      </tbody>
    </table>
    """


def report_html(*tables: str, as_of: str = "2026년 08월 31일") -> str:
    return f"""
    <div id="doc-">
      <table border="1">
        <tr><td>직위</td><td>변경 전<br/>성명</td><td>변경 후<br/>성명</td><td>변경사유</td></tr>
        <tr><td>비상임이사</td><td>이전임원</td><td>현재임원</td><td>인사이동</td></tr>
      </table>
      {"".join(tables)}
      <table border="1"><tr><td>기준일</td><td>{as_of}</td><td>제출일</td><td>2026년 08월 31일</td></tr></table>
      <table border="1">
        <tr><th>구분</th><th>담당자명</th><th>부서명</th><th>전화번호</th></tr>
        <tr><td>작성자</td><td>{STAFF_NAME}</td><td>경영공시부</td><td>{STAFF_PHONE}</td></tr>
      </table>
    </div>
    """


class FakeAlioProvider:
    def __init__(self) -> None:
        self.institutions = [
            {
                "apbaId": "C0001",
                "apbaNa": "테스트공기업",
                "apbaType": "A2002",
                "typeNa": "공기업(준시장형)",
            },
            {
                "apbaId": "C0002",
                "apbaNa": "테스트준정부기관",
                "apbaType": "A2004",
                "typeNa": "준정부기관(위탁집행형)",
            },
        ]
        self.disclosures = {
            "C0001": "2026083100000001",
            "C0002": "2026083100000002",
        }
        self.documents = {
            "2026083100000001": report_html(
                executive_table("김기관"),
                executive_table(
                    "박감사", position="비상임감사", title="비상임감사", career="회계법인 대표"
                ),
            ),
            "2026083100000002": report_html(
                executive_table("이전문", position="상임이사", title="디지털본부장")
            ),
        }
        self.fail_once_for: str | None = None
        self.requests: list[tuple[str, str, dict | None]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, payload))
        if request.url.path == "/item/itemOrganListSusi.json":
            assert request.method == "POST"
            assert payload == {
                "apbaType": [],
                "apbaId": "",
                "reportFormRootNo": "20305",
            }
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "totalCnt": len(self.institutions),
                        "organList": self.institutions,
                    },
                },
            )
        if request.url.path == "/item/itemReportListSusi.json":
            assert request.method == "POST"
            assert payload is not None
            institution_code = payload["apbaId"]
            assert payload["pageNo"] == 1
            assert payload["reportFormRootNo"] == "20305"
            assert payload["search_word"] == ""
            if self.fail_once_for == institution_code:
                self.fail_once_for = None
                return httpx.Response(503)
            disclosure_no = self.disclosures[institution_code]
            return httpx.Response(
                200,
                json={
                    "status": "success",
                    "data": {
                        "result": [
                            {
                                "rnum": 1,
                                "disclosureNo": disclosure_no,
                                "reportFormNo": "20305",
                                "apbaId": institution_code,
                                "reportGbn": "Y",
                                "idate": "2026.08.31",
                            }
                        ],
                        "page": {
                            "currPage": 1,
                            "unitPage": 10,
                            "totalCount": 1,
                            "totalPage": 1,
                        },
                    },
                },
            )
        if request.url.path == "/item/itemReport.do":
            disclosure_no = request.url.params["disclosureNo"]
            assert request.url.params["seq"] == disclosure_no
            path = f"/upload/disclosure/2026/08/31/{disclosure_no}/doc.html"
            return httpx.Response(200, text=f'<script>$(".doc_con").load("{path}")</script>')
        if request.url.path.startswith("/upload/disclosure/"):
            disclosure_no = request.url.path.split("/")[-2]
            return httpx.Response(200, text=self.documents[disclosure_no])
        raise AssertionError(f"unexpected ALIO request: {request.method} {request.url}")

    def connector(self) -> AlioExecutiveDisclosureConnector:
        return AlioExecutiveDisclosureConnector(transport=httpx.MockTransport(self.handle))


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def test_alio_connector_uses_exact_item_4_contract_and_parses_current_report() -> None:
    provider = FakeAlioProvider()
    connector = provider.connector()
    directory_document = connector.fetch(connector.discover()[0])
    directory = connector.parse_directory_body(directory_document.body)
    assert directory.total_count == 2
    assert [item.institution_code for item in directory.institutions] == ["C0001", "C0002"]

    list_document = connector.fetch(connector.report_list_url(directory.institutions[0]))
    page = connector.parse_report_page_body(
        list_document.body, institution_code="C0001", requested_page=1
    )
    current = connector.current_disclosure(page)
    assert current.disclosure_no == "2026083100000001"
    assert page.page_size == 10

    report = connector.fetch(connector.report_url(current))
    records = connector.parse_executives(
        report, institution=directory.institutions[0], disclosure=current
    )
    assert [item.record_id for item in records] == [
        "2026083100000001:1",
        "2026083100000001:2",
    ]
    assert records[0].person_name == "김기관"
    assert records[0].reported_careers == ("테스트부 차관", "테스트청장")
    assert records[0].as_of.isoformat() == "2026-08-31"
    assert STAFF_NAME not in repr(records)
    assert STAFF_PHONE not in repr(records)


def test_full_current_roster_persists_all_institutions_and_minimized_rows(
    tmp_path: Path,
) -> None:
    provider = FakeAlioProvider()
    repository = migrated_repository(tmp_path / "full.db")

    result = AlioExecutiveEnumerator(provider.connector(), repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.institutions_committed == 2
    assert result.unique_records == 3
    checkpoint = repository.source_checkpoint(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "2"
    assert checkpoint.metadata["institution_total"] == 2
    observations = repository.feeder_observations(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )
    assert len(observations) == 3
    payload = json.dumps(
        [item.model_dump(mode="json") for item in observations], ensure_ascii=False
    )
    assert STAFF_NAME not in payload
    assert STAFF_PHONE not in payload
    assert '"provider_person_id": null' in payload
    assert "성별" not in payload

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    assert len(sources) == 3
    assert all("apbaId" not in row.url or "C000" in row.url for row in sources)
    assert all(row.fulltext is None for row in snapshots)
    persisted = repr([(row.url, row.title) for row in sources]) + repr(
        [row.metadata_json for row in snapshots]
    )
    assert STAFF_NAME not in persisted
    assert STAFF_PHONE not in persisted


def test_unchanged_rerun_is_idempotent_and_changed_row_is_immutable(tmp_path: Path) -> None:
    provider = FakeAlioProvider()
    repository = migrated_repository(tmp_path / "versions.db")
    enumerator = AlioExecutiveEnumerator(provider.connector(), repository)
    first = enumerator.enumerate()
    second = enumerator.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    assert (
        len(
            repository.feeder_observations(
                AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
            )
        )
        == 3
    )

    disclosure = provider.disclosures["C0001"]
    provider.documents[disclosure] = report_html(
        executive_table("김기관", career="변경된 주요경력"),
        executive_table(
            "박감사", position="비상임감사", title="비상임감사", career="회계법인 대표"
        ),
    )
    changed = enumerator.enumerate()
    versions = repository.feeder_observations(
        AlioExecutiveEnumerator.FEEDER,
        AlioExecutiveEnumerator.SCOPE_KEY,
        f"{disclosure}:1",
    )
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    assert len(versions) == 2
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_resumes_from_last_committed_institution(tmp_path: Path) -> None:
    provider = FakeAlioProvider()
    provider.fail_once_for = "C0002"
    repository = migrated_repository(tmp_path / "resume.db")
    enumerator = AlioExecutiveEnumerator(provider.connector(), repository)

    with pytest.raises(AlioRecordError, match="request failed"):
        enumerator.enumerate()

    partial = repository.source_runs(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )[-1]
    checkpoint = repository.source_checkpoint(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )
    assert partial.status == SourceRunStatus.PARTIAL
    assert checkpoint is not None
    assert checkpoint.cursor == "1"

    resumed = enumerator.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.institutions_committed == 1
    assert (
        len(
            repository.feeder_observations(
                AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
            )
        )
        == 3
    )


def test_resume_fails_closed_when_institution_universe_changes(tmp_path: Path) -> None:
    provider = FakeAlioProvider()
    provider.fail_once_for = "C0002"
    repository = migrated_repository(tmp_path / "changed-directory.db")
    enumerator = AlioExecutiveEnumerator(provider.connector(), repository)
    with pytest.raises(AlioRecordError):
        enumerator.enumerate()

    provider.institutions[0] = {**provider.institutions[0], "apbaNa": "기관명변경"}
    with pytest.raises(AlioRecordError, match="universe changed"):
        enumerator.enumerate(resume=True)
    assert repository.source_runs()[-1].status == SourceRunStatus.FAILED


def test_checkpoint_does_not_advance_when_second_institution_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeAlioProvider()
    repository = migrated_repository(tmp_path / "atomic.db")
    original = repository.commit_source_page

    def fail_second_institution(**kwargs):
        if kwargs["cursor"] == "2":
            raise RuntimeError("synthetic commit failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_institution)
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        AlioExecutiveEnumerator(provider.connector(), repository).enumerate()

    checkpoint = repository.source_checkpoint(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "1"
    assert (
        len(
            repository.feeder_observations(
                AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
            )
        )
        == 2
    )
    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda payload: payload["data"].update(totalCnt=3), "coverage is incomplete"),
        (
            lambda payload: payload["data"]["organList"].append(payload["data"]["organList"][0]),
            "duplicate ALIO institution",
        ),
    ],
)
def test_directory_coverage_failures_are_rejected(mutation, message: str) -> None:
    provider = FakeAlioProvider()
    payload = {
        "status": "success",
        "data": {
            "totalCnt": 2,
            "organList": [dict(item) for item in provider.institutions],
        },
    }
    mutation(payload)
    with pytest.raises(AlioRecordError, match=message):
        AlioExecutiveDisclosureConnector.parse_directory_body(json.dumps(payload))


@pytest.mark.parametrize(
    ("page_update", "message"),
    [
        ({"currPage": 2}, "pagination is inconsistent"),
        ({"unitPage": 20}, "pagination is inconsistent"),
        ({"totalPage": 2}, "total-page coverage"),
    ],
)
def test_report_pagination_failures_are_rejected(page_update: dict, message: str) -> None:
    payload = {
        "status": "success",
        "data": {
            "result": [
                {
                    "rnum": 1,
                    "disclosureNo": "2026083100000001",
                    "reportFormNo": "20305",
                    "apbaId": "C0001",
                    "reportGbn": "Y",
                    "idate": "2026.08.31",
                }
            ],
            "page": {
                "currPage": 1,
                "unitPage": 10,
                "totalCount": 1,
                "totalPage": 1,
                **page_update,
            },
        },
    }
    with pytest.raises(AlioRecordError, match=message):
        AlioExecutiveDisclosureConnector.parse_report_page_body(
            json.dumps(payload), institution_code="C0001", requested_page=1
        )


def test_missing_current_rank_and_masked_executive_fail_closed() -> None:
    provider = FakeAlioProvider()
    connector = provider.connector()
    directory_document = connector.fetch(connector.discover()[0])
    institution = connector.parse_directory_body(directory_document.body).institutions[0]
    list_document = connector.fetch(connector.report_list_url(institution))
    page = connector.parse_report_page_body(
        list_document.body, institution_code="C0001", requested_page=1
    )
    missing_current = page.__class__(
        tuple(replace_rank(item, 2) for item in page.disclosures),
        page.page_no,
        page.page_size,
        page.total_count,
        page.total_pages,
    )
    with pytest.raises(AlioRecordError, match="current item 4"):
        connector.current_disclosure(missing_current)

    disclosure = connector.current_disclosure(page)
    provider.documents[disclosure.disclosure_no] = report_html(executive_table("○○○"))
    report = connector.fetch(connector.report_url(disclosure))
    with pytest.raises(AlioRecordError, match="masked or vacant"):
        connector.parse_executives(report, institution=institution, disclosure=disclosure)


def replace_rank(item, rank: int):
    return item.__class__(
        rank=rank,
        disclosure_no=item.disclosure_no,
        institution_code=item.institution_code,
        report_form_no=item.report_form_no,
        disclosure_date=item.disclosure_date,
    )


def test_policy_denial_happens_before_network_or_run(tmp_path: Path) -> None:
    provider = FakeAlioProvider()
    repository = migrated_repository(tmp_path / "policy.db")
    denied = alio_public_institution_policy().model_copy(update={"can_fetch": False})
    with pytest.raises(PolicyDenied):
        AlioExecutiveEnumerator(provider.connector(), repository, denied).enumerate()
    assert provider.requests == []
    assert repository.source_runs() == []


def test_alio_identity_materialization_is_review_required_without_person_creation(
    tmp_path: Path,
) -> None:
    provider = FakeAlioProvider()
    repository = migrated_repository(tmp_path / "review.db")
    AlioExecutiveEnumerator(provider.connector(), repository).enumerate()
    observation = repository.feeder_observations(
        AlioExecutiveEnumerator.FEEDER, AlioExecutiveEnumerator.SCOPE_KEY
    )[0]

    result = repository.materialize_feeder_observation(observation.id)

    assert result.decision.action == MaterializationAction.REVIEW_REQUIRED
    assert result.decision.decision_class == MaterializationDecisionClass.UNSUPPORTED_FEEDER
    assert result.review_item_id is not None
    assert repository.people() == []
    reviews = repository.identity_review_items(IdentityReviewStatus.OPEN)
    assert len(reviews) == 1
    assert reviews[0].observation_id == observation.id
