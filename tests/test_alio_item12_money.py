from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from apps.api.main import create_app
from packages.connectors.alio_disclosures import (
    AlioInstitutionHeadBusinessExpenseConnector,
    AlioRecordError,
    alio_public_institution_policy,
    parse_item12_directory_body,
)
from packages.domain.contracts import (
    Claim,
    FeederObservation,
    Organization,
    Source,
    SourceSnapshot,
)
from packages.domain.db import (
    ClaimRow,
    IdentityReviewItemRow,
    OrganizationRow,
    PersonObservationLinkRow,
    PersonRow,
    SourceRow,
    SourceSnapshotRow,
)
from packages.domain.enums import SourceRunStatus
from packages.persistence import OrganizationClaimImportError, SqlAlchemyRepository
from packages.rendering.money_projection import (
    build_alio_head_expense_claim,
    build_alio_head_expense_money,
)
from packages.verification.policy import PolicyDenied
from workers.alio_business_expense import (
    AlioBusinessExpenseEnumerator,
    alio_business_expense_content_hash,
    normalized_alio_business_expense,
)

STAFF_NAME = "수집하지않는공시담당자"
STAFF_PHONE = "02-9999-9999"
REPORT_FORM_NO = "20701"
REPORT_PERIOD = "2026-Q1"


def business_expense_html(
    amounts: dict[int, int],
    attachment_names: dict[int, str],
    *,
    institution_name: str = "테스트정보기관",
    unit: str = "천원",
) -> str:
    rows = "".join(
        f"<tr><td>{year}년</td><td>{amount:,}</td>"
        f"<td><a href=\"javascript:report_attach_down('{attachment_names[year]}')\">"
        f"{attachment_names[year]}</a></td></tr>"
        for year in sorted(amounts, reverse=True)
        for amount in (amounts[year],)
    )
    return f"""
    <div id="doc-">
      <table><tr><td>(2026년 1/4분기)</td></tr></table>
      <table><tr><td>{institution_name}</td></tr></table>
      <table><tr><td>(단위: {unit})</td></tr></table>
      <table border="1">
        <thead><tr><th>연도</th><th>업무추진비 집행금액</th><th>집행상세내역</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      <table border="1"><tr><td>기준일</td><td>2025년 12월 31일</td>
        <td>제출일</td><td>2026년 04월 13일</td></tr></table>
      <table border="1">
        <tr><th>구분</th><th>담당자명</th><th>부서명</th><th>전화번호</th></tr>
        <tr><td>작성자</td><td>{STAFF_NAME}</td><td>공시관리팀</td><td>{STAFF_PHONE}</td></tr>
      </table>
    </div>
    """


def directory_row(
    code: str,
    name: str,
    institution_type: str,
    disclosure_no: str | None,
    submission_no: str,
    extension: str,
) -> dict[str, object]:
    files = (
        "@"
        if disclosure_no is None
        else "|".join(
            f"{101 + index}@{year}년 기관장 업무추진비.{extension}"
            for index, year in enumerate(range(2025, 2020, -1))
        )
    )
    return {
        "apbaId": code,
        "apbaNa": name,
        "typeNa": institution_type,
        "jidtNa": "테스트부처",
        "critYyyy": "2026",
        "critQuar": "1",
        "quartNa": "1분기",
        "reportFormNo": REPORT_FORM_NO,
        "reportParnFormNo": None,
        "span": "1",
        "submissionNo": submission_no,
        "disclosureNo": disclosure_no,
        "files": files,
    }


def directory_payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return {"status": "success", "data": {"totalCnt": len(rows), "organList": rows}}


class FakeAlioMoneyProvider:
    def __init__(self) -> None:
        self.rows = [
            directory_row(
                "C0019",
                "테스트교통공단",
                "준정부기관(위탁집행형)",
                "2026091400000001",
                "2026091400001001",
                "xlsx",
            ),
            directory_row(
                "C0129",
                "테스트기술진흥원",
                "기타공공기관",
                "2026091400000002",
                "2026091400001002",
                "xlsx",
            ),
            directory_row(
                "C0908",
                "테스트정보기관",
                "준정부기관(위탁집행형)",
                "2026091400000003",
                "2026091400001003",
                "xls",
            ),
        ]
        self.amounts: dict[str, dict[int, int]] = {
            "C0019": {2021: 100, 2022: 200, 2023: 300, 2024: 400, 2025: 500},
            "C0129": {2021: 1100, 2022: 1200, 2023: 1300, 2024: 1400, 2025: 1500},
            "C0908": {2021: 12277, 2022: 20118, 2023: 13396, 2024: 15023, 2025: 12861},
        }
        self.documents = {
            row["disclosureNo"]: business_expense_html(
                self.amounts[row["apbaId"]],
                {
                    year: f"{year}년 기관장 업무추진비.{('xls' if row['apbaId'] == 'C0908' else 'xlsx')}"
                    for year in range(2025, 2020, -1)
                },
                institution_name=str(row["apbaNa"]),
            )
            for row in self.rows
            if row["disclosureNo"] is not None
        }
        self.requests: list[tuple[str, str, dict | None]] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content) if request.content else None
        self.requests.append((request.method, request.url.path, payload))
        if request.url.path == "/item/itemOrganListJung.json":
            assert request.method == "POST"
            assert payload == {
                "apbaType": [],
                "jidtDptm": [],
                "area": [],
                "apbaId": "",
                "reportFormRootNo": REPORT_FORM_NO,
                "quart": "",
            }
            return httpx.Response(200, json=directory_payload(self.rows))
        if request.url.path == "/mobile/item/itemReportTerm.do":
            assert request.method == "GET"
            disclosure_no = request.url.params["disclosureNo"]
            row = next(item for item in self.rows if item["disclosureNo"] == disclosure_no)
            assert request.url.params["apbaId"] == row["apbaId"]
            assert request.url.params["reportFormRootNo"] == REPORT_FORM_NO
            assert request.url.params["nowYear"] == "2026"
            assert request.url.params["nowQuarter"] == "1"
            path = f"/upload/disclosure/2026/09/14/{disclosure_no}/doc.html"
            return httpx.Response(
                200,
                text=(
                    f'<script>$(".doc_con").load("{path}")</script>'
                    f'<input id="submission_no" value="{row["submissionNo"]}"/>'
                ),
            )
        if request.url.path.startswith("/upload/disclosure/"):
            disclosure_no = request.url.path.split("/")[-2]
            return httpx.Response(200, text=self.documents[disclosure_no])
        raise AssertionError(f"unexpected ALIO request: {request.method} {request.url}")

    def connector(self) -> AlioInstitutionHeadBusinessExpenseConnector:
        return AlioInstitutionHeadBusinessExpenseConnector(
            transport=httpx.MockTransport(self.handle)
        )


def migrated_repository(database: Path) -> SqlAlchemyRepository:
    database_url = f"sqlite:///{database.as_posix()}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    return SqlAlchemyRepository(database_url)


def test_item12_parser_reads_five_annual_rows_and_minimizes_contacts() -> None:
    provider = FakeAlioMoneyProvider()
    connector = provider.connector()
    directory = connector.parse_directory_body(connector.fetch(connector.discover()[0]).body)
    assert directory.total_count == 3
    assert len({row.institution_code for row in directory.rows}) == 3
    row = next(item for item in directory.rows if item.institution_code == "C0908")

    document = connector.fetch(connector.report_url(row))
    records = connector.parse_business_expense_rows(document, directory_row=row)

    assert len(records) == 5
    assert records[0].fiscal_year == 2025
    assert records[0].amount_thousand_krw == 12861
    assert records[0].amount_krw == 12861000
    assert records[0].report_period == REPORT_PERIOD
    assert records[0].report_period_label == "2026년 1/4분기"
    assert records[0].as_of_date.isoformat() == "2025-12-31"
    assert records[0].submission_date.isoformat() == "2026-04-13"
    assert records[0].detail_attachment_name.endswith(".xls")
    assert records[0].detail_attachment_locator == (
        "submission:2026091400001003:filename:2025년 기관장 업무추진비.xls"
    )
    assert STAFF_NAME not in repr(records)
    assert STAFF_PHONE not in repr(records)


def test_item12_directory_preserves_explicit_no_data_without_inventing_report() -> None:
    row = directory_row(
        "C0459",
        "명시적무공시기관",
        "기타공공기관",
        None,
        "2026091400001004",
        "xlsx",
    )
    parsed = parse_item12_directory_body(json.dumps(directory_payload([row])))

    assert parsed.rows[0].disclosure_no is None
    assert parsed.rows[0].detail_attachment_names == ()


def test_item12_directory_rejects_non_spreadsheet_attachment() -> None:
    row = directory_row(
        "C0908",
        "테스트정보기관",
        "준정부기관(위탁집행형)",
        "2026091400000003",
        "2026091400001003",
        "pdf",
    )

    with pytest.raises(AlioRecordError, match="attachment format"):
        parse_item12_directory_body(json.dumps(directory_payload([row])))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: replace(
                document, body=document.body.replace("(단위: 천원)", "(단위: 원)")
            ),
            "amount unit",
        ),
        (
            lambda document: replace(document, body=document.body.replace(">15,023<", ">15.02<")),
            "amount is missing or malformed",
        ),
        (
            lambda document: replace(document, body=document.body.replace(">2023년<", ">2024년<")),
            "fiscal year is duplicate",
        ),
        (
            lambda document: replace(
                document,
                metadata={**document.metadata, "institution_code": "C0000"},
            ),
            "institution identity",
        ),
    ],
)
def test_item12_parser_fails_closed_on_contract_breaks(mutation, message: str) -> None:
    provider = FakeAlioMoneyProvider()
    connector = provider.connector()
    directory = connector.parse_directory_body(connector.fetch(connector.discover()[0]).body)
    row = next(item for item in directory.rows if item.institution_code == "C0908")
    document = mutation(connector.fetch(connector.report_url(row)))

    with pytest.raises(AlioRecordError, match=message):
        connector.parse_business_expense_rows(document, directory_row=row)


def test_bounded_item12_enumerator_persists_observations_without_persons(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "item12.db")
    enumerator = AlioBusinessExpenseEnumerator(
        provider.connector(),
        repository,
        institution_codes=("C0908", "C0129", "C0019"),
    )

    result = enumerator.enumerate()

    assert result.run.status == SourceRunStatus.SUCCESS
    assert result.institutions_committed == 3
    assert result.unique_records == 15
    observations = repository.feeder_observations(
        enumerator.FEEDER,
        enumerator.scope_key,
    )
    assert len(observations) == 15
    assert all(item.identity_hints == {} for item in observations)
    payload = json.dumps(
        [item.model_dump(mode="json") for item in observations], ensure_ascii=False
    )
    assert STAFF_NAME not in payload
    assert STAFF_PHONE not in payload

    with repository.sessions() as session:
        sources = list(session.scalars(select(SourceRow)))
        snapshots = list(session.scalars(select(SourceSnapshotRow)))
        assert list(session.scalars(select(PersonRow))) == []
        assert list(session.scalars(select(PersonObservationLinkRow))) == []
        assert list(session.scalars(select(IdentityReviewItemRow))) == []
        assert list(session.scalars(select(ClaimRow))) == []
    assert len(sources) == 4
    assert len(snapshots) == 4
    assert all(row.fulltext is None for row in snapshots)
    persisted = repr([(row.url, row.title) for row in sources]) + repr(
        [row.metadata_json for row in snapshots]
    )
    assert STAFF_NAME not in persisted
    assert STAFF_PHONE not in persisted


def test_item12_policy_denial_happens_before_network_or_run(tmp_path: Path) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "policy.db")
    denied = alio_public_institution_policy().model_copy(update={"can_fetch": False})

    with pytest.raises(PolicyDenied):
        AlioBusinessExpenseEnumerator(provider.connector(), repository, denied).enumerate()

    assert provider.requests == []
    assert repository.source_runs() == []


def test_item12_rerun_is_idempotent_and_changed_amount_is_a_new_version(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "versions.db")
    enumerator = AlioBusinessExpenseEnumerator(provider.connector(), repository)

    first = enumerator.enumerate()
    second = enumerator.enumerate()
    assert first.run.observations_created == 15
    assert second.run.observations_created == 0
    assert second.run.observations_unchanged == 15

    changed_disclosure = next(
        row["disclosureNo"] for row in provider.rows if row["apbaId"] == "C0908"
    )
    assert isinstance(changed_disclosure, str)
    provider.documents[changed_disclosure] = provider.documents[changed_disclosure].replace(
        ">15,023<", ">16,000<"
    )
    third = enumerator.enumerate()

    assert third.run.observations_created == 1
    assert third.run.observations_unchanged == 14
    versions = repository.feeder_observations(
        enumerator.FEEDER,
        enumerator.scope_key,
        f"{changed_disclosure}:2024",
    )
    assert len(versions) == 2
    assert {item.normalized["amount_krw"] for item in versions} == {15023000, 16000000}
    assert len({item.content_hash for item in versions}) == 2


def _money_inputs(
    repository: SqlAlchemyRepository,
    observations,
) -> tuple[dict[UUID, SourceSnapshot], dict[UUID, Source]]:
    snapshots: dict[UUID, SourceSnapshot] = {}
    sources: dict[UUID, Source] = {}
    for observation in observations:
        snapshot = repository.source_snapshot(observation.snapshot_id)
        assert snapshot is not None
        source = repository.source(snapshot.source_id)
        assert source is not None
        snapshots[snapshot.id] = snapshot
        sources[source.id] = source
    return snapshots, sources


def test_item12_money_derivation_is_deterministic_and_provenance_complete(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "money.db")
    enumerator = AlioBusinessExpenseEnumerator(provider.connector(), repository)
    enumerator.enumerate()
    observations = [
        item
        for item in repository.feeder_observations(enumerator.FEEDER, enumerator.scope_key)
        if item.normalized["institution_code"] == "C0908"
    ]
    snapshots, sources = _money_inputs(repository, observations)

    result = build_alio_head_expense_money(
        observations,
        snapshots=snapshots,
        sources=sources,
        earlier_fiscal_year=2024,
        later_fiscal_year=2025,
    )

    assert result["kind"] == "MONEY"
    assert result["method_version"] == "money.alio-head-expense-yoy.v1"
    assert result["claim_id"] is None
    assert result["publication_status"] == "BLOCKED"
    assert result["details"]["absolute_delta_krw"] == -2162000
    assert result["details"]["percent_change"] == "-14.39"
    earlier = result["details"]["earlier"]
    later = result["details"]["later"]
    assert earlier["amount_krw"] == 15023000
    assert later["amount_krw"] == 12861000
    assert result["observation_ids"] == [earlier["observation_id"], later["observation_id"]]
    assert result["snapshot_ids"] == [earlier["snapshot_id"]]
    assert result["source_ids"] == [earlier["source_id"]]
    assert result["details"]["provenance"]["earlier"] == {
        "observation_id": earlier["observation_id"],
        "snapshot_id": earlier["snapshot_id"],
        "source_id": earlier["source_id"],
    }
    assert result["details"]["provenance"]["later"] == {
        "observation_id": later["observation_id"],
        "snapshot_id": later["snapshot_id"],
        "source_id": later["source_id"],
    }


def test_item12_money_zero_baseline_is_explicitly_unavailable() -> None:
    provider = FakeAlioMoneyProvider()
    connector = provider.connector()
    directory = connector.parse_directory_body(connector.fetch(connector.discover()[0]).body)
    row = next(item for item in directory.rows if item.institution_code == "C0908")
    document = connector.fetch(connector.report_url(row))
    records = connector.parse_business_expense_rows(document, directory_row=row)
    normalized = [normalized_alio_business_expense(record) for record in records]
    observations = [
        FeederObservation(
            feeder="alio_institution_head_business_expense",
            scope_key="item_12_current_known_positive:C0908",
            provider_record_key=f"{row.disclosure_no}:{record.fiscal_year}",
            snapshot_id=UUID("50000000-0000-0000-0000-000000000001"),
            run_id=UUID("50000000-0000-0000-0000-000000000002"),
            provider_observed_at=datetime(2025, 12, 31, tzinfo=UTC),
            semantic_scope="institutional_head_business_expense_annual_disclosure",
            identity_hints={},
            normalized={
                **item,
                "amount_thousand_krw": 0
                if record.fiscal_year == 2024
                else item["amount_thousand_krw"],
                "amount_krw": 0 if record.fiscal_year == 2024 else item["amount_krw"],
            },
            content_hash=alio_business_expense_content_hash(
                {
                    **item,
                    "amount_thousand_krw": 0
                    if record.fiscal_year == 2024
                    else item["amount_thousand_krw"],
                    "amount_krw": 0 if record.fiscal_year == 2024 else item["amount_krw"],
                }
            ),
        )
        for record, item in zip(records, normalized, strict=True)
        if record.fiscal_year in {2024, 2025}
    ]
    source = Source(
        url="https://alio.go.kr/mobile/item/itemReportTerm.do?apbaId=C0908&reportFormRootNo=20701&disclosureNo=2026091400000003&nowYear=2026&nowQuarter=1",
        title="ALIO Item 12",
        publisher="재정경제부",
        policy_id=alio_public_institution_policy().id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash="a" * 64,
        metadata={
            "source_contract": "alio_item_12_current_institution_head_business_expense",
            "report_form_no": "20701",
            "institution_code": "C0908",
            "disclosure_no": "2026091400000003",
            "submission_no": "2026091400001003",
            "report_period": "2026-Q1",
            "document_path": "/upload/disclosure/2026/09/14/2026091400000003/doc.html",
        },
        fulltext=None,
    )
    snapshots = {snapshot.id: snapshot}
    sources = {source.id: source}
    # The source-specific read model needs exact snapshot references; rebuild the two inputs.
    observations = [item.model_copy(update={"snapshot_id": snapshot.id}) for item in observations]

    result = build_alio_head_expense_money(
        observations,
        snapshots=snapshots,
        sources=sources,
        earlier_fiscal_year=2024,
        later_fiscal_year=2025,
    )

    assert result["details"]["absolute_delta_krw"] == 12861000
    assert result["details"]["percent_change"] is None


def test_item12_public_api_has_no_organization_money_bypass() -> None:
    paths = {route.path for route in create_app().routes}

    assert "/money" not in paths
    assert "/organizations" not in paths
    assert "/organizations/{organization_id}" in paths
    assert "/organizations/{organization_id}/claims" in paths
    assert "/people/{person_id}/assets" in paths


def test_item12_observation_versions_are_ambiguous_until_selected() -> None:
    provider = FakeAlioMoneyProvider()
    connector = provider.connector()
    directory = connector.parse_directory_body(connector.fetch(connector.discover()[0]).body)
    row = next(item for item in directory.rows if item.institution_code == "C0908")
    document = connector.fetch(connector.report_url(row))
    records = connector.parse_business_expense_rows(document, directory_row=row)
    source = Source(
        url="https://alio.go.kr/mobile/item/itemReportTerm.do?apbaId=C0908&reportFormRootNo=20701&disclosureNo=2026091400000003&nowYear=2026&nowQuarter=1",
        title="ALIO Item 12",
        publisher="재정경제부",
        policy_id=alio_public_institution_policy().id,
    )
    snapshot = SourceSnapshot(
        source_id=source.id,
        content_hash="b" * 64,
        metadata={
            "source_contract": "alio_item_12_current_institution_head_business_expense",
            "report_form_no": "20701",
            "institution_code": "C0908",
            "disclosure_no": "2026091400000003",
            "submission_no": "2026091400001003",
            "report_period": "2026-Q1",
            "document_path": "/upload/disclosure/2026/09/14/2026091400000003/doc.html",
        },
    )
    record = next(item for item in records if item.fiscal_year == 2024)
    normalized = normalized_alio_business_expense(record)
    first = FeederObservation(
        feeder="alio_institution_head_business_expense",
        scope_key="item_12_current_known_positive:C0908",
        provider_record_key=f"{record.disclosure_no}:2024",
        snapshot_id=snapshot.id,
        run_id=UUID("50000000-0000-0000-0000-000000000002"),
        provider_observed_at=datetime(2025, 12, 31, tzinfo=UTC),
        semantic_scope="institutional_head_business_expense_annual_disclosure",
        identity_hints={},
        normalized=normalized,
        content_hash=alio_business_expense_content_hash(normalized),
    )
    changed_normalized = {**normalized, "amount_thousand_krw": 16000, "amount_krw": 16000000}
    second = first.model_copy(
        update={
            "id": UUID("50000000-0000-0000-0000-000000000003"),
            "normalized": changed_normalized,
            "content_hash": alio_business_expense_content_hash(changed_normalized),
        }
    )

    with pytest.raises(ValueError, match="multiple immutable versions"):
        build_alio_head_expense_money(
            [first, second],
            snapshots={snapshot.id: snapshot},
            sources={source.id: source},
            earlier_fiscal_year=2024,
            later_fiscal_year=2024 + 1,
        )


def test_claim_subject_requires_exactly_one_person_or_organization() -> None:
    fields = {
        "proposition": "기관은 공시액을 발표했다.",
        "subject": "기관",
        "predicate": "DISCLOSED_BUSINESS_EXPENSE",
        "object_text": "100천원",
        "epistemic_status": "FACT",
        "publication_status": "PUBLISHED",
        "asserted_as_true": True,
    }

    with pytest.raises(ValidationError, match="exactly one"):
        Claim.model_validate(fields)
    with pytest.raises(ValidationError, match="exactly one"):
        Claim.model_validate(
            fields
            | {
                "person_id": UUID("70000000-0000-0000-0000-000000000001"),
                "organization_id": UUID("70000000-0000-0000-0000-000000000002"),
            }
        )


def test_item12_claim_builder_and_publication_reuse_canonical_evidence_path(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "organization-claim.db")
    enumerator = AlioBusinessExpenseEnumerator(provider.connector(), repository)
    enumerator.enumerate()

    observation = next(
        item
        for item in repository.feeder_observations(enumerator.FEEDER, enumerator.scope_key)
        if item.provider_record_key.endswith(":2025")
        and item.normalized["institution_code"] == "C0908"
    )
    snapshots, sources = _money_inputs(repository, [observation])
    source = sources[next(iter(sources))]
    policy = repository.policies([source.policy_id])[source.policy_id]
    organization = Organization(
        id=UUID("60000000-0000-0000-0000-000000000001"),
        name="테스트정보기관",
    )
    with repository.sessions() as session:
        session.add(
            OrganizationRow(
                id=str(organization.id),
                name=organization.name,
                valid_from=organization.valid_from,
                valid_to=organization.valid_to,
                recorded_at=organization.recorded_at,
                superseded_at=organization.superseded_at,
            )
        )
        session.commit()

    claim, evidence = build_alio_head_expense_claim(
        observation,
        organization=organization,
        policy=policy,
        snapshots=snapshots,
        sources=sources,
    )
    assert claim.person_id is None
    assert claim.organization_id == organization.id
    assert claim.predicate == "DISCLOSED_BUSINESS_EXPENSE"
    assert claim.qualifiers["institution_code"] == "C0908"
    assert evidence.feeder_observation_id == observation.id
    assert evidence.snapshot_id == observation.snapshot_id
    assert evidence.excerpt is None

    repository.import_organization_claim(organization, claim, [evidence])
    stored = repository.claims(
        published_only=True,
        current_only=True,
        organization_id=organization.id,
    )
    assert [item.id for item in stored] == [claim.id]
    assert stored[0].person_id is None
    assert stored[0].organization_id == organization.id

    with TestClient(create_app(repository)) as client:
        response = client.get(f"/organizations/{organization.id}/claims")
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 1
        assert payload[0]["organization_id"] == str(organization.id)
        assert payload[0]["person_id"] is None
        assert payload[0]["evidence"][0]["feeder_observation_id"] == str(observation.id)
        assert payload[0]["evidence"][0]["snapshot_id"] == str(observation.snapshot_id)

        organization_response = client.get(f"/organizations/{organization.id}")
        assert organization_response.status_code == 200
        assert len(organization_response.json()["claims"]) == 1


def test_organization_claim_import_rejects_ambiguous_observation_versions(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "organization-claim-version.db")
    enumerator = AlioBusinessExpenseEnumerator(provider.connector(), repository)
    enumerator.enumerate()

    provider.amounts["C0908"][2024] = 16000
    provider.documents["2026091400000003"] = business_expense_html(
        provider.amounts["C0908"],
        {
            year: f"{year}년 기관장 업무추진비.xls"
            for year in range(2025, 2020, -1)
        },
        institution_name="테스트정보기관",
    )
    enumerator.enumerate()

    observation = next(
        item
        for item in repository.feeder_observations(enumerator.FEEDER, enumerator.scope_key)
        if item.provider_record_key == "2026091400000003:2024"
        and item.normalized["amount_krw"] == 16000000
    )
    snapshots, sources = _money_inputs(repository, [observation])
    source = sources[next(iter(sources))]
    policy = repository.policies([source.policy_id])[source.policy_id]
    organization = Organization(
        id=UUID("60000000-0000-0000-0000-000000000003"),
        name="테스트정보기관",
    )
    with repository.sessions() as session:
        session.add(
            OrganizationRow(
                id=str(organization.id),
                name=organization.name,
                valid_from=organization.valid_from,
                valid_to=organization.valid_to,
                recorded_at=organization.recorded_at,
                superseded_at=organization.superseded_at,
            )
        )
        session.commit()

    claim, evidence = build_alio_head_expense_claim(
        observation,
        organization=organization,
        policy=policy,
        snapshots=snapshots,
        sources=sources,
    )

    with pytest.raises(
        OrganizationClaimImportError,
        match="multiple immutable observation versions",
    ):
        repository.import_organization_claim(organization, claim, [evidence])

    assert repository.claims(organization_id=organization.id) == []


def test_organization_claim_import_does_not_materialize_provider_identity(
    tmp_path: Path,
) -> None:
    provider = FakeAlioMoneyProvider()
    repository = migrated_repository(tmp_path / "organization-identity.db")
    enumerator = AlioBusinessExpenseEnumerator(provider.connector(), repository)
    enumerator.enumerate()
    observation = next(
        item
        for item in repository.feeder_observations(enumerator.FEEDER, enumerator.scope_key)
        if item.provider_record_key == "2026091400000003:2025"
    )
    snapshots, sources = _money_inputs(repository, [observation])
    source = sources[next(iter(sources))]
    policy = repository.policies([source.policy_id])[source.policy_id]
    organization = Organization(
        id=UUID("60000000-0000-0000-0000-000000000002"),
        name="테스트정보기관",
    )
    claim, evidence = build_alio_head_expense_claim(
        observation,
        organization=organization,
        policy=policy,
        snapshots=snapshots,
        sources=sources,
    )

    with pytest.raises(OrganizationClaimImportError, match="existing canonical"):
        repository.import_organization_claim(organization, claim, [evidence])

    assert repository.organization(organization.id) is None
    assert repository.claims(organization_id=organization.id) == []
