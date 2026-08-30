from pathlib import Path

import httpx
import pytest

from packages.connectors.base import ConnectorDocument
from packages.connectors.nkis_research import (
    MissingNkisApiKey,
    NkisResearchReportConnector,
    nkis_research_policy,
    responsible_researcher_candidate_name,
)
from workers.policy_research import (
    output_to_identity,
    repeated_research_topics,
    stage_outputs,
)

FIXTURE = Path(__file__).parent / "fixtures" / "nkis_research_reports.xml"
SECRET = "nkis-secret-must-not-persist"


def fixture_xml() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def fixture_document() -> ConnectorDocument:
    return ConnectorDocument(
        url="https://nkis.re.kr/nkisApi/search/ReportList.do?pageNo=1&rowCnt=30",
        title="NKIS 연구보고서 목록",
        publisher="경제·인문사회연구회 국가정책연구포털",
        published_at=None,
        body=fixture_xml(),
        metadata={"total_count": "3"},
    )


def test_nkis_policy_is_metadata_only_and_commercial_ai_use_fail_closed() -> None:
    policy = nkis_research_policy()
    assert policy.domain == "nkis.re.kr"
    assert policy.can_fetch
    assert policy.can_store_metadata
    assert not policy.can_store_fulltext
    assert not policy.can_send_to_ai
    assert not policy.can_show_excerpt
    assert not policy.can_commercialize


def test_discovery_url_never_contains_api_key() -> None:
    connector = NkisResearchReportConnector(
        api_key=SECRET,
        title="인공지능",
        publisher="테스트정책연구원",
        year_begin=2025,
        year_end=2026,
    )
    url = httpx.URL(connector.discover()[0])
    assert url.host == "nkis.re.kr"
    assert url.params["otpHanNm"] == "인공지능"
    assert url.params["pubagc"] == "테스트정책연구원"
    assert "serviceKey" not in url.params
    assert SECRET not in str(url)


def test_missing_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NKIS_API_KEY", raising=False)
    connector = NkisResearchReportConnector(
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected fetch: {request}"))
    )
    with pytest.raises(MissingNkisApiKey):
        connector.fetch(connector.discover()[0])


def test_fetch_injects_key_only_outbound_and_redacts_echoed_service_key() -> None:
    response_xml = fixture_xml().replace(
        "<root>", f"<root><serviceKey>{SECRET}</serviceKey>", 1
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["serviceKey"] == SECRET
        return httpx.Response(200, text=response_xml)

    connector = NkisResearchReportConnector(api_key=SECRET, transport=httpx.MockTransport(handler))
    document = connector.fetch(connector.discover()[0])
    assert SECRET not in document.url
    assert SECRET not in document.body
    assert document.metadata["total_count"] == "3"


def test_report_parser_preserves_research_output_without_employment_claim() -> None:
    outputs = NkisResearchReportConnector.parse_outputs(fixture_document())
    assert len(outputs) == 3
    assert outputs[0].output_id == "OTP_TEST_001"
    assert outputs[0].responsible_researcher_text == "김연구"
    assert outputs[0].publisher == "테스트정책연구원"

    candidate = output_to_identity(outputs[0])
    assert candidate is not None
    assert candidate.canonical_name == "김연구"
    assert candidate.organization is None
    assert candidate.office == "연구책임자(해당 연구성과)"
    assert "nkis_publisher:테스트정책연구원" in candidate.career_anchors

    staged = stage_outputs(outputs)[0].to_dict()
    assert "researcher_candidate" in staged
    assert "author_candidate" not in staged


def test_ambiguous_or_generic_researcher_text_never_creates_person_candidate() -> None:
    assert responsible_researcher_candidate_name("박정책 외 2인") is None
    assert responsible_researcher_candidate_name("연구원") is None
    assert responsible_researcher_candidate_name("김정책, 이연구") is None

    outputs = NkisResearchReportConnector.parse_outputs(fixture_document())
    staged = stage_outputs(outputs)
    assert staged[2].candidate is None


def test_repeated_topics_require_distinct_outputs() -> None:
    outputs = NkisResearchReportConnector.parse_outputs(fixture_document())
    topics = repeated_research_topics(outputs)
    assert topics == [
        {
            "topic": "인공지능 산업정책",
            "output_count": 2,
            "semantics": "DERIVED_FROM_MULTIPLE_OUTPUTS",
        }
    ]
    assert repeated_research_topics(outputs[:1]) == []
    assert repeated_research_topics([outputs[0], outputs[0]]) == []
    with pytest.raises(ValueError, match="at least two outputs"):
        repeated_research_topics(outputs, minimum_outputs=1)
