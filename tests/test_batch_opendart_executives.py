import json
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from packages.connectors.open_dart_corporate import (
    DartApiError,
    DartCorporateDataset,
    MissingDartApiKey,
    OpenDartCorpCodeConnector,
    OpenDartCorporateConnector,
    open_dart_corporate_policy,
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
from workers.corporate_talent import OpenDartExecutiveEnumerator

SECRET = "dart-secret-must-not-persist"
PRIVATE_FIELD = "private@example.invalid"


def corporation_archive(rows: list[dict[str, str]]) -> bytes:
    row_xml = "".join(
        "<list>"
        f"<corp_code>{row['corp_code']}</corp_code>"
        f"<corp_name>{row['corp_name']}</corp_name>"
        f"<corp_eng_name>{row.get('corp_eng_name', '')}</corp_eng_name>"
        f"<stock_code>{row.get('stock_code', '')}</stock_code>"
        f"<modify_date>{row['modify_date']}</modify_date>"
        "</list>"
        for row in rows
    )
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("CORPCODE.xml", f"<?xml version='1.0'?><result>{row_xml}</result>")
    return stream.getvalue()


def executive_row(
    corp_code: str,
    corp_name: str,
    receipt_no: str,
    name: str,
    *,
    career: str,
) -> dict[str, object]:
    return {
        "rcept_no": receipt_no,
        "corp_cls": "Y",
        "corp_code": corp_code,
        "corp_name": corp_name,
        "nm": name,
        "sexdstn": "남",
        "birth_ym": "1975년 04월",
        "ofcps": "대표이사",
        "rgist_exctv_at": "등기임원",
        "fte_at": "상근",
        "chrg_job": "대표이사",
        "main_career": career,
        "mxmm_shrholdr_relate": "본인",
        "hffc_pd": "2024.03~현재",
        "tenure_end_on": "2027-03-25",
        "stlm_dt": "2026-06-30",
        "private_email": PRIVATE_FIELD,
    }


class FakeOpenDartProvider:
    def __init__(self) -> None:
        self.corporations = [
            {
                "corp_code": "00000003",
                "corp_name": "감마테크",
                "corp_eng_name": "Gamma Tech",
                "stock_code": "",
                "modify_date": "20260829",
            },
            {
                "corp_code": "00000001",
                "corp_name": "알파테크",
                "corp_eng_name": "Alpha Tech",
                "stock_code": "123456",
                "modify_date": "20260831",
            },
            {
                "corp_code": "00000002",
                "corp_name": "베타테크",
                "corp_eng_name": "Beta Tech",
                "stock_code": "654321",
                "modify_date": "20260830",
            },
        ]
        self.executives: dict[str, dict[str, object]] = {
            "00000001": {
                "status": "000",
                "message": "정상",
                "list": [
                    executive_row(
                        "00000001",
                        "알파테크",
                        "20260831000001",
                        "김대표",
                        career="알파산업 부사장",
                    ),
                    executive_row(
                        "00000001",
                        "알파테크",
                        "20260831000001",
                        "이사외",
                        career="알파연구소장",
                    ),
                ],
            },
            "00000002": {"status": "013", "message": "조회된 데이터가 없습니다."},
            "00000003": {
                "status": "000",
                "message": "정상",
                "list": [
                    executive_row(
                        "00000003",
                        "감마테크",
                        "20260831000003",
                        "박대표",
                        career="감마산업 전무",
                    )
                ],
            },
        }
        self.fail_once_for: str | None = None
        self.failed = False
        self.requests: list[tuple[str, str | None]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        assert request.url.params["crtfc_key"] == SECRET
        corp_code = request.url.params.get("corp_code")
        self.requests.append((request.url.path, corp_code))
        if request.url.path == "/api/corpCode.xml":
            return httpx.Response(200, content=corporation_archive(self.corporations))
        if request.url.path == "/api/exctvSttus.json":
            assert request.url.params["bsns_year"] == "2026"
            assert request.url.params["reprt_code"] == "11012"
            if self.fail_once_for == corp_code and not self.failed:
                self.failed = True
                raise httpx.ReadError("synthetic provider failure", request=request)
            assert corp_code is not None
            return httpx.Response(200, json=self.executives[corp_code])
        raise AssertionError(f"unexpected OpenDART request: {request.url}")

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)

    def universe_connector(self) -> OpenDartCorpCodeConnector:
        return OpenDartCorpCodeConnector(api_key=SECRET, transport=self.transport())

    def executive_connector(self, corp_code: str) -> OpenDartCorporateConnector:
        return OpenDartCorporateConnector(
            dataset=DartCorporateDataset.EXECUTIVE_STATUS,
            corp_code=corp_code,
            business_year=2026,
            report_code="11012",
            api_key=SECRET,
            transport=self.transport(),
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def enumerator(
    provider: FakeOpenDartProvider,
    repository: SqlAlchemyRepository,
    *,
    policy=None,
) -> OpenDartExecutiveEnumerator:
    return OpenDartExecutiveEnumerator(
        provider.universe_connector(),
        repository,
        business_year=2026,
        report_code="11012",
        executive_connector_factory=provider.executive_connector,
        policy=policy,
    )


def test_corp_code_master_uses_exact_zip_contract_and_sorted_unique_universe() -> None:
    provider = FakeOpenDartProvider()
    connector = provider.universe_connector()

    document = connector.fetch(connector.discover()[0])
    corporations = connector.parse_corporations(document)

    assert [item.corp_code for item in corporations] == ["00000001", "00000002", "00000003"]
    assert corporations[0].stock_code == "123456"
    assert corporations[2].stock_code is None
    assert document.metadata["record_count"] == "3"
    serialized = json.dumps(
        {"url": document.url, "body": document.body, "metadata": document.metadata},
        ensure_ascii=False,
    )
    assert "crtfc_key" not in serialized
    assert SECRET not in serialized


def test_full_corp_master_scope_persists_complete_minimized_executive_observations(
    tmp_path: Path,
) -> None:
    provider = FakeOpenDartProvider()
    repository = migrated_repository(tmp_path / "full.db")

    result = enumerator(provider, repository).enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.corporations_committed == 3
    assert result.corporations_covered == 3
    assert result.companies_with_executives == 2
    assert result.companies_without_executives == 1
    assert result.unique_records == 3
    checkpoint = repository.source_checkpoint(
        OpenDartExecutiveEnumerator.FEEDER, result.run.scope_key
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "3"
    assert checkpoint.metadata["corporation_total"] == 3
    assert checkpoint.metadata["last_corp_code"] == "00000003"
    observations = repository.feeder_observations(
        OpenDartExecutiveEnumerator.FEEDER, result.run.scope_key
    )
    assert [item.provider_record_key for item in observations] == [
        "00000001:20260831000001:1",
        "00000001:20260831000001:2",
        "00000003:20260831000003:1",
    ]
    payload = json.dumps(
        [item.model_dump(mode="json") for item in observations], ensure_ascii=False
    )
    assert '"provider_person_id": null' in payload
    assert '"birth_year_month": "1975년 04월"' in payload
    assert "sexdstn" not in payload
    assert PRIVATE_FIELD not in payload
    assert SECRET not in payload
    assert "employee" not in payload.casefold()
    assert "compensation" not in payload.casefold()

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
    persisted = json.dumps(
        {
            "sources": [(row.url, row.title) for row in sources],
            "snapshots": [row.metadata_json for row in snapshots],
        },
        ensure_ascii=False,
    )
    assert all(row.fulltext is None for row in snapshots)
    assert "crtfc_key" not in persisted
    assert SECRET not in persisted
    assert PRIVATE_FIELD not in persisted


def test_unchanged_rerun_is_idempotent_and_changed_disclosure_row_is_immutable(
    tmp_path: Path,
) -> None:
    provider = FakeOpenDartProvider()
    repository = migrated_repository(tmp_path / "versions.db")
    worker = enumerator(provider, repository)

    first = worker.enumerate()
    second = worker.enumerate()

    assert first.run.observations_created == 3
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 3
    first_row = provider.executives["00000001"]["list"][0]
    assert isinstance(first_row, dict)
    first_row["main_career"] = "변경된 회사 공시 주요경력"

    changed = worker.enumerate()
    versions = repository.feeder_observations(
        OpenDartExecutiveEnumerator.FEEDER,
        changed.run.scope_key,
        "00000001:20260831000001:1",
    )
    assert changed.run.observations_created == 1
    assert changed.run.observations_unchanged == 2
    assert len(versions) == 2
    assert len({item.content_hash for item in versions}) == 2


def test_partial_failure_resumes_from_last_committed_corporation(tmp_path: Path) -> None:
    provider = FakeOpenDartProvider()
    provider.fail_once_for = "00000002"
    repository = migrated_repository(tmp_path / "resume.db")
    worker = enumerator(provider, repository)

    with pytest.raises(DartApiError, match="request failed"):
        worker.enumerate()

    partial = repository.source_runs(OpenDartExecutiveEnumerator.FEEDER, worker.scope_key)[-1]
    checkpoint = repository.source_checkpoint(OpenDartExecutiveEnumerator.FEEDER, worker.scope_key)
    assert partial.status == SourceRunStatus.PARTIAL
    assert checkpoint is not None
    assert checkpoint.cursor == "1"

    resumed = worker.enumerate(resume=True)
    assert resumed.run.status == SourceRunStatus.SUCCESS
    assert resumed.corporations_committed == 2
    assert resumed.corporations_covered == 3
    assert resumed.unique_records == 3


def test_resume_fails_closed_when_corporation_universe_changes(tmp_path: Path) -> None:
    provider = FakeOpenDartProvider()
    provider.fail_once_for = "00000002"
    repository = migrated_repository(tmp_path / "changed-universe.db")
    worker = enumerator(provider, repository)
    with pytest.raises(DartApiError):
        worker.enumerate()

    provider.corporations[0] = {**provider.corporations[0], "corp_name": "감마테크변경"}
    with pytest.raises(DartApiError, match="universe changed"):
        worker.enumerate(resume=True)
    assert repository.source_runs()[-1].status == SourceRunStatus.FAILED


def test_checkpoint_does_not_advance_when_corporation_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeOpenDartProvider()
    repository = migrated_repository(tmp_path / "atomic.db")
    original = repository.commit_source_page

    def fail_second_corporation(**kwargs):
        if kwargs["cursor"] == "2":
            raise RuntimeError("synthetic commit failure")
        return original(**kwargs)

    monkeypatch.setattr(repository, "commit_source_page", fail_second_corporation)
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        enumerator(provider, repository).enumerate()

    checkpoint = repository.source_checkpoint(
        OpenDartExecutiveEnumerator.FEEDER, "all_corporations:2026:11012"
    )
    assert checkpoint is not None
    assert checkpoint.cursor == "1"
    assert repository.source_runs()[-1].status == SourceRunStatus.PARTIAL


def test_duplicate_corporation_code_and_mismatched_executive_company_fail_closed(
    tmp_path: Path,
) -> None:
    duplicate_provider = FakeOpenDartProvider()
    duplicate_provider.corporations.append(dict(duplicate_provider.corporations[0]))
    with pytest.raises(DartApiError, match="duplicate OpenDART corporation code"):
        duplicate_provider.universe_connector().fetch(
            duplicate_provider.universe_connector().discover()[0]
        )

    mismatch_provider = FakeOpenDartProvider()
    mismatch_row = mismatch_provider.executives["00000001"]["list"][0]
    assert isinstance(mismatch_row, dict)
    mismatch_row["corp_code"] = "99999999"
    repository = migrated_repository(tmp_path / "mismatch.db")
    with pytest.raises(DartApiError, match="corporation code mismatch"):
        enumerator(mismatch_provider, repository).enumerate()


def test_policy_denial_and_missing_key_happen_before_network_or_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DART_API_KEY", raising=False)
    missing = OpenDartCorpCodeConnector(
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}"))
    )
    with pytest.raises(MissingDartApiKey):
        missing.fetch(missing.discover()[0])

    provider = FakeOpenDartProvider()
    repository = migrated_repository(tmp_path / "policy.db")
    denied = open_dart_corporate_policy().model_copy(update={"can_fetch": False})
    with pytest.raises(PolicyDenied):
        enumerator(provider, repository, policy=denied).enumerate()
    assert provider.requests == []
    assert repository.source_runs() == []


def test_opendart_identity_materialization_is_review_required_without_person_creation(
    tmp_path: Path,
) -> None:
    provider = FakeOpenDartProvider()
    repository = migrated_repository(tmp_path / "review.db")
    result = enumerator(provider, repository).enumerate()
    observation = repository.feeder_observations(
        OpenDartExecutiveEnumerator.FEEDER, result.run.scope_key
    )[0]

    materialized = repository.materialize_feeder_observation(observation.id)

    assert materialized.decision.action == MaterializationAction.REVIEW_REQUIRED
    assert materialized.decision.decision_class == MaterializationDecisionClass.UNSUPPORTED_FEEDER
    assert materialized.review_item_id is not None
    assert repository.people() == []
    reviews = repository.identity_review_items(IdentityReviewStatus.OPEN)
    assert len(reviews) == 1
    assert reviews[0].observation_id == observation.id
