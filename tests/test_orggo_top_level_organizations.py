import httpx
import pytest

from packages.connectors.orggo_top_level_organizations import (
    OrgGoTopLevelOrganizationConnector,
    OrgGoTopLevelOrganizationError,
    orggo_top_level_organization_policy,
)
from packages.domain.enums import SourceCollectionMode


def page_html(*rows: tuple[str, str, str, str], total: int = 63) -> str:
    anchors = "\n".join(
        (
            f'<a href="javascript:openDetail(\'{category}\',\'{org_code}\',\'{chart_id}\')" '
            f'title="{name} detail" class="subject">{name}</a>'
        )
        for name, category, org_code, chart_id in rows
    )
    return f"""
    <!DOCTYPE html>
    <html lang="ko"><body><div>총 {total} 건</div>{anchors}</body></html>
    """


def transport_for(body: str) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.org.go.kr"
        assert request.url.path == "/cop/bbs/getInstiChartList.do"
        return httpx.Response(200, text=body, headers={"content-type": "text/html; charset=utf-8"})
    return httpx.MockTransport(handler)


def test_policy_is_conservative_metadata_only() -> None:
    policy = orggo_top_level_organization_policy()
    assert policy.domain == "www.org.go.kr"
    assert policy.collection_mode == SourceCollectionMode.HTTP
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_show_excerpt is False
    assert policy.can_commercialize is False
    assert policy.license is None


def test_discovery_is_bounded_to_one_page() -> None:
    connector = OrgGoTopLevelOrganizationConnector(page_index=3)
    url = httpx.URL(connector.discover()[0])
    assert url.scheme == "https"
    assert url.host == "www.org.go.kr"
    assert url.path == "/cop/bbs/getInstiChartList.do"
    assert url.params["pageIndex"] == "3"


def test_fetch_parses_metadata_and_rows() -> None:
    body = page_html(
        ("재정경제부", "중앙행정기관", "1053000", "63"),
        ("과학기술정보통신부", "중앙행정기관", "1721000", "60"),
    )
    connector = OrgGoTopLevelOrganizationConnector(page_index=1, transport=transport_for(body))
    document = connector.fetch(connector.discover()[0])
    assert document.metadata["row_count"] == "2"
    assert document.metadata["total_count"] == "63"
    records = connector.parse_organizations(document)
    assert [record.organization_name for record in records] == ["재정경제부", "과학기술정보통신부"]
    assert records[0].category == "중앙행정기관"
    assert records[0].org_code == "1053000"
    assert records[0].chart_id == "63"


def test_query_scope_rejects_unknown_or_invalid_page() -> None:
    connector = OrgGoTopLevelOrganizationConnector()
    with pytest.raises(ValueError, match="unsupported"):
        connector.fetch(connector.discover()[0] + "&search=x")
    with pytest.raises(ValueError, match="integer"):
        connector.fetch("https://www.org.go.kr/cop/bbs/getInstiChartList.do?pageIndex=bad")
    with pytest.raises(ValueError, match=">= 1"):
        OrgGoTopLevelOrganizationConnector(page_index=0)


def test_malformed_subject_locator_fails_closed() -> None:
    body = """
    <html><body><div>총 63 건</div>
    <a class="subject" href="javascript:openDetail('중앙행정기관','bad','63')">재정경제부</a>
    </body></html>
    """
    with pytest.raises(OrgGoTopLevelOrganizationError, match="malformed detail locator"):
        OrgGoTopLevelOrganizationConnector.parse_page_body(body)


def test_duplicate_org_code_fails_closed() -> None:
    body = page_html(
        ("재정경제부", "중앙행정기관", "1053000", "63"),
        ("재정경제부 중복", "중앙행정기관", "1053000", "64"),
    )
    with pytest.raises(OrgGoTopLevelOrganizationError, match="duplicate orgCode"):
        OrgGoTopLevelOrganizationConnector.parse_page_body(body)


def test_missing_total_count_fails_closed() -> None:
    body = """
    <html><body>
    <a class="subject" href="javascript:openDetail('중앙행정기관','1053000','63')">재정경제부</a>
    </body></html>
    """
    with pytest.raises(OrgGoTopLevelOrganizationError, match="total count"):
        OrgGoTopLevelOrganizationConnector.parse_page_body(body)


def test_ambiguous_total_count_fails_closed() -> None:
    body = page_html(("재정경제부", "중앙행정기관", "1053000", "63"))
    body = body.replace("</body>", "<div>총 62 건</div></body>")
    with pytest.raises(OrgGoTopLevelOrganizationError, match="total count"):
        OrgGoTopLevelOrganizationConnector.parse_page_body(body)


def test_row_count_cannot_exceed_provider_total() -> None:
    body = page_html(
        ("재정경제부", "중앙행정기관", "1053000", "63"),
        ("과학기술정보통신부", "중앙행정기관", "1721000", "60"),
        total=1,
    )
    with pytest.raises(OrgGoTopLevelOrganizationError, match="exceeds provider total"):
        OrgGoTopLevelOrganizationConnector.parse_page_body(body)
