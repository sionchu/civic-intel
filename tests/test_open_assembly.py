import httpx
import pytest

from packages.connectors.open_assembly import (
    AssemblyApiError,
    MissingAssemblyApiKey,
    OpenAssemblyMemberConnector,
    national_assembly_member_policy,
)
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied
from workers.ingest import IngestionPipeline

SECRET = "test-secret-must-never-persist"


def member_payload(*, result_code: str = "INFO-000") -> dict:
    return {
        OpenAssemblyMemberConnector.API_CODE: [
            {
                "head": [
                    {"list_total_count": 1},
                    {"RESULT": {"CODE": result_code, "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {
                "row": [
                    {
                        "MONA_CD": "ABC123",
                        "HG_NM": "홍길동",
                        "HJ_NM": "洪吉童",
                        "ENG_NM": "Hong Gil-dong",
                        "BTH_DATE": "1970-01-02",
                        "POLY_NM": "테스트정당",
                        "ORIG_NM": "서울 테스트구",
                        "REELE_GBN_NM": "재선",
                        "ELECT_GBN_NM": "지역구",
                        "CMITS": "테스트위원회",
                        "TEL_NO": "02-0000-0000",
                        "E_MAIL": "private-ish@example.invalid",
                        "KEY": SECRET,
                    }
                ]
            },
        ]
    }


def success_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        assert request.url.host == OpenAssemblyMemberConnector.HOST
        return httpx.Response(200, json=member_payload())

    return httpx.MockTransport(handler)


def test_missing_api_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASSEMBLY_API_KEY", raising=False)
    connector = OpenAssemblyMemberConnector(
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}"))
    )
    with pytest.raises(MissingAssemblyApiKey, match="ASSEMBLY_API_KEY"):
        connector.fetch(connector.discover()[0])


def test_discovery_url_is_sanitized_and_filterable() -> None:
    connector = OpenAssemblyMemberConnector(
        api_key=SECRET,
        page_index=2,
        page_size=50,
        name="홍길동",
        party="테스트정당",
        district="서울 테스트구",
    )
    url = connector.discover()[0]
    parsed = httpx.URL(url)
    assert parsed.scheme == "https"
    assert parsed.host == OpenAssemblyMemberConnector.HOST
    assert parsed.path == OpenAssemblyMemberConnector.PATH
    assert parsed.params["Type"] == "json"
    assert parsed.params["pIndex"] == "2"
    assert parsed.params["pSize"] == "50"
    assert parsed.params["HG_NM"] == "홍길동"
    assert parsed.params["POLY_NM"] == "테스트정당"
    assert parsed.params["ORIG_NM"] == "서울 테스트구"
    assert SECRET not in url
    assert "KEY" not in parsed.params


def test_successful_fetch_parses_identity_safe_member_fields() -> None:
    connector = OpenAssemblyMemberConnector(api_key=SECRET, transport=success_transport())
    document = connector.fetch(connector.discover()[0])
    members = connector.parse_members(document)

    assert document.publisher == "국회 국회사무처"
    assert document.metadata["row_count"] == "1"
    assert document.metadata["list_total_count"] == "1"
    assert SECRET not in document.url
    assert SECRET not in document.body
    assert SECRET not in repr(document.metadata)

    assert len(members) == 1
    member = members[0]
    assert member.member_code == "ABC123"
    assert member.name_ko == "홍길동"
    assert member.name_hanja == "洪吉童"
    assert member.name_en == "Hong Gil-dong"
    assert member.birth_date is not None
    assert member.birth_date.isoformat() == "1970-01-02"
    assert member.party == "테스트정당"
    assert member.district == "서울 테스트구"
    assert member.committees == "테스트위원회"
    assert not hasattr(member, "telephone")
    assert not hasattr(member, "email")


def test_provider_error_does_not_leak_api_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["KEY"] == SECRET
        return httpx.Response(200, json=member_payload(result_code="INFO-200"))

    connector = OpenAssemblyMemberConnector(api_key=SECRET, transport=httpx.MockTransport(handler))
    with pytest.raises(AssemblyApiError) as exc_info:
        connector.fetch(connector.discover()[0])
    assert "INFO-200" in str(exc_info.value)
    assert SECRET not in str(exc_info.value)


def test_policy_denial_happens_before_connector_fetch() -> None:
    def forbidden_handler(request: httpx.Request) -> httpx.Response:
        pytest.fail(f"policy denial should happen before network fetch: {request}")

    connector = OpenAssemblyMemberConnector(
        api_key=SECRET, transport=httpx.MockTransport(forbidden_handler)
    )
    blocked = national_assembly_member_policy().model_copy(
        update={"collection_mode": SourceCollectionMode.BLOCKED, "can_fetch": False}
    )
    with pytest.raises(PolicyDenied):
        IngestionPipeline(connector).ingest(connector.discover()[0], blocked)


def test_reviewed_policy_minimizes_raw_storage() -> None:
    policy = national_assembly_member_policy()
    assert policy.can_fetch
    assert policy.can_store_metadata
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert policy.can_commercialize
    assert policy.license == "이용허락범위 제한 없음"

    connector = OpenAssemblyMemberConnector(api_key=SECRET, transport=success_transport())
    result = IngestionPipeline(connector).ingest(connector.discover()[0], policy)
    assert result.snapshot.fulltext is None
    assert SECRET not in str(result.source.url)
    assert SECRET not in repr(result.snapshot.metadata)
