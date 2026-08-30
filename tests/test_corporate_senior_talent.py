import json
from pathlib import Path

import httpx
import pytest

from packages.connectors.company_official_profiles import (
    CompanyProfileRecordError,
    parse_company_official_profile_rows,
)
from packages.connectors.open_dart_corporate import (
    DartCorporateDataset,
    MissingDartApiKey,
    OpenDartCorporateConnector,
    open_dart_corporate_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.identity import IdentityStatus, resolve_identity
from packages.verification.policy import PolicyDenied
from workers.corporate_talent import (
    OpenDartCorporateStager,
    compensation_to_dict,
    render_corporate_json,
    stage_company_official_profiles,
    stage_dart_executives,
    stage_dart_ownership,
)

FIXTURE = Path(__file__).parent / "fixtures" / "corporate_senior_talent.json"
SECRET = "dart-secret-must-not-persist"


def fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def mock_transport(payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["crtfc_key"] == SECRET
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_open_dart_policy_allows_metadata_fetch_but_commercial_ai_use_fail_closed() -> None:
    policy = open_dart_corporate_policy()
    assert policy.domain == "opendart.fss.or.kr"
    assert policy.can_fetch
    assert policy.can_store_metadata
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert not policy.can_commercialize


def test_dart_discovery_url_never_contains_api_key() -> None:
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.EXECUTIVE_STATUS,
        corp_code="00123456",
        business_year=2026,
        report_code="11012",
        api_key=SECRET,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.host == "opendart.fss.or.kr"
    assert url.params["corp_code"] == "00123456"
    assert url.params["bsns_year"] == "2026"
    assert url.params["reprt_code"] == "11012"
    assert "crtfc_key" not in url.params
    assert SECRET not in str(url)


def test_missing_dart_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DART_API_KEY", raising=False)
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.EXECUTIVE_STATUS,
        corp_code="00123456",
        business_year=2026,
        report_code="11012",
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}")),
    )
    with pytest.raises(MissingDartApiKey):
        connector.fetch(connector.discover()[0])


def test_dart_executive_status_stages_registered_and_disclosed_nonregistered_executives() -> None:
    payload = fixture()["dart_executive_status"]
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.EXECUTIVE_STATUS,
        corp_code="00123456",
        business_year=2026,
        report_code="11012",
        api_key=SECRET,
        transport=mock_transport(payload),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse(document)
    staged = stage_dart_executives(records)  # type: ignore[arg-type]

    assert len(staged) == 2
    assert staged[0].candidate.canonical_name == "김대표"
    assert staged[0].candidate.organization == "테스트테크"
    assert staged[1].candidate.canonical_name == "이기술"
    assert staged[1].record.registered_status == "미등기임원"
    assert resolve_identity(staged[0].candidate, staged[0].candidate).status == IdentityStatus.RESOLVED

    rendered = render_corporate_json({"executives": [item.to_dict() for item in staged]})
    assert "private@example.invalid" not in rendered
    assert "20260830000001" in rendered
    assert "원 공시 추적키" in rendered


def test_compensation_is_enrichment_only_and_never_new_person_or_total_wealth() -> None:
    payload = fixture()["dart_compensation_v2"]
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.TOP_COMPENSATION_V2,
        corp_code="00123456",
        business_year=2026,
        report_code="11012",
        api_key=SECRET,
        transport=mock_transport(payload),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse(document)
    output = [compensation_to_dict(record) for record in records]  # type: ignore[arg-type]

    assert output[0]["disclosed_name"] == "김대표"
    assert output[0]["person_candidate"] is None
    assert output[1]["disclosed_name"] == "최고액"
    assert output[1]["person_candidate"] is None
    assert output[0]["wealth_semantics"] == "DISCLOSED_COMPENSATION_NOT_TOTAL_WEALTH"


def test_dart_ownership_can_stage_public_officer_or_major_holder_without_conflict_inference() -> None:
    payload = fixture()["dart_ownership"]
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.OFFICER_MAJOR_HOLDER_OWNERSHIP,
        corp_code="00123456",
        api_key=SECRET,
        transport=mock_transport(payload),
    )
    records = connector.parse(connector.fetch(connector.discover()[0]))
    staged = stage_dart_ownership(records)  # type: ignore[arg-type]

    assert staged[0].candidate is not None
    assert staged[0].candidate.canonical_name == "김대표"
    data = staged[0].to_dict()
    assert data["ownership_disclosure"]["security_rate"] == 12.5
    serialized = json.dumps(data, ensure_ascii=False)
    assert "이해충돌" in serialized
    assert "자동 의미하지 않는다" in serialized


def test_source_policy_denial_happens_before_dart_fetch() -> None:
    connector = OpenDartCorporateConnector(
        dataset=DartCorporateDataset.EXECUTIVE_STATUS,
        corp_code="00123456",
        business_year=2026,
        report_code="11012",
        api_key=SECRET,
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}")),
    )
    policy = open_dart_corporate_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        OpenDartCorporateStager(connector, policy).stage()


def test_company_official_profile_can_stage_public_technical_leader_without_dart_role() -> None:
    row = fixture()["company_official_profiles"][0]
    records = parse_company_official_profile_rows([row])
    assert records[0].public_scope == "TECH_CENTER_HEAD"
    staged = stage_company_official_profiles([row])[0]
    assert staged.candidate.canonical_name == "하AI"
    assert staged.candidate.office == "퓨처AI센터장"
    assert staged.candidate.organization == "테스트클라우드"
    serialized = json.dumps(staged.to_dict(), ensure_ascii=False)
    assert "DART 등기임원 여부와 별도 근거" in serialized
    assert "010-9999-9999" not in serialized
    assert "private@example.invalid" not in serialized


def test_company_official_profile_rejects_ordinary_employee_and_unreviewed_source() -> None:
    ordinary = fixture()["company_official_profiles"][1]
    with pytest.raises(CompanyProfileRecordError, match="ordinary/non-senior"):
        parse_company_official_profile_rows([ordinary])

    unreviewed = fixture()["company_official_profiles"][0] | {"source_policy_ref": "UNREVIEWED"}
    with pytest.raises(CompanyProfileRecordError, match="reviewed SourcePolicy"):
        parse_company_official_profile_rows([unreviewed])
