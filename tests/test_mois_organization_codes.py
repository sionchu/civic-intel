import json
from datetime import date

import httpx
import pytest

from packages.connectors.mois_organization_codes import (
    MissingMoisOrganizationCodeApiKey,
    MoisOrganizationCodeApiError,
    MoisOrganizationCodeConnector,
    mois_organization_code_policy,
)
from packages.domain.enums import SourceCollectionMode

SECRET = "mois-secret-must-not-persist"


def organization_row(**overrides) -> dict:
    row = {
        "org_cd": "1741000",
        "full_nm": "행정안전부",
        "low_nm": "행정안전부",
        "abbr_nm": "행안부",
        "gap_no": "1",
        "rank_no": "023",
        "sub_chasu": "0",
        "high_cd": "0000000",
        "highst_cd": "1741000",
        "rep_cd": "1741000",
        "typebig_nm": "국가행정기관",
        "typemid_nm": "중앙행정기관 및 이에 준하는 기관",
        "typesml_nm": "부",
        "locatstd_cd": "36110",
        "use_cd": "1741000",
        "crt_de": "20170726",
        "cls_de": "",
        "stop_selt": "0",
        "chg_de": "20191018",
        "base_date": "20170724",
        "adpt_date": "20191018",
        "preorg_cd": "",
    }
    row.update(overrides)
    return row


def response_payload(rows: list[dict], *, total: int | None = None) -> dict:
    return {
        "response": {
            "header": {"resultCode": "INFO-0", "resultMsg": "NORMAL SERVICE"},
            "body": {
                "pageNo": 1,
                "numOfRows": 100,
                "totalCount": len(rows) if total is None else total,
                "items": {"item": rows},
            },
        }
    }

def transport_for(payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["ServiceKey"] == SECRET
        assert request.url.params["stop_selt"] == "0"
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_policy_matches_reviewed_data_go_contract() -> None:
    policy = mois_organization_code_policy()
    assert policy.domain == "apis.data.go.kr"
    assert policy.collection_mode == SourceCollectionMode.API
    assert policy.can_fetch is True
    assert policy.can_store_metadata is True
    assert policy.can_store_fulltext is False
    assert policy.can_send_to_ai is False
    assert policy.can_commercialize is True
    assert policy.license == "이용허락범위 제한 없음"


def test_discovery_is_current_only_and_contains_no_secret() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        full_name="행정안전부",
        org_code="1741000",
    )
    url = httpx.URL(connector.discover()[0])
    assert url.scheme == "https"
    assert url.host == "apis.data.go.kr"
    assert url.path == "/1741000/StanOrgCd2/getStanOrgCdList2"
    assert url.params["type"] == "json"
    assert url.params["stop_selt"] == "0"
    assert url.params["full_nm"] == "행정안전부"
    assert url.params["org_cd"] == "1741000"
    assert "ServiceKey" not in url.params
    assert SECRET not in str(url)


def test_missing_key_blocks_live_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOIS_ORG_CODE_API_KEY", raising=False)
    connector = MoisOrganizationCodeConnector(
        transport=httpx.MockTransport(lambda request: pytest.fail(f"unexpected: {request}"))
    )
    with pytest.raises(MissingMoisOrganizationCodeApiKey):
        connector.fetch(connector.discover()[0])


def test_fetch_injects_then_redacts_service_key() -> None:
    payload = response_payload([organization_row()])
    payload["debug"] = {"ServiceKey": SECRET, "keep": "safe"}
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(payload),
    )
    document = connector.fetch(connector.discover()[0])
    body = json.loads(document.body)
    assert body["debug"] == {"keep": "safe"}
    assert SECRET not in document.body
    assert SECRET not in document.url
    assert SECRET not in json.dumps(document.metadata, ensure_ascii=False)
    assert document.metadata["source_contract"] == "mois_standard_organization_code_v1"
    assert document.metadata["row_count"] == "1"
    assert document.metadata["total_count"] == "1"
    assert document.metadata["provider_page_no"] == "1"
    assert document.metadata["provider_page_size"] == "100"
    assert document.metadata["stop_selt"] == "0"


def test_parser_preserves_provider_identity_hierarchy_and_dates() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(response_payload([organization_row()])),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_organizations(document)
    assert len(records) == 1
    record = records[0]
    assert record.org_code == "1741000"
    assert record.full_name == "행정안전부"
    assert record.lowest_name == "행정안전부"
    assert record.abbreviation == "행안부"
    assert record.parent_org_code == "0000000"
    assert record.top_org_code == "1741000"
    assert record.representative_org_code == "1741000"
    assert record.type_big == "국가행정기관"
    assert record.type_mid == "중앙행정기관 및 이에 준하는 기관"
    assert record.type_small == "부"
    assert record.use_code == "1741000"
    assert record.created_date == date(2017, 7, 26)
    assert record.changed_date == date(2019, 10, 18)
    assert record.base_date == date(2017, 7, 24)
    assert record.applied_date == date(2019, 10, 18)
    assert record.closed_date is None
    assert record.stop_selector == "0"
    assert record.previous_org_code is None


def test_connector_rejects_credentials_in_discovery_url() -> None:
    connector = MoisOrganizationCodeConnector(api_key=SECRET)
    with pytest.raises(ValueError, match="credentials"):
        connector.fetch(
            connector.discover()[0] + f"&ServiceKey={SECRET}"
        )


def test_connector_rejects_non_current_scope() -> None:
    connector = MoisOrganizationCodeConnector(api_key=SECRET)
    url = connector.discover()[0].replace("stop_selt=0", "stop_selt=1")
    with pytest.raises(ValueError, match="current-institution"):
        connector.fetch(url)


def test_parser_rejects_invalid_org_code() -> None:
    document = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(response_payload([organization_row(org_cd="17410")])),
    ).fetch(MoisOrganizationCodeConnector(api_key=SECRET).discover()[0])
    with pytest.raises(MoisOrganizationCodeApiError, match="invalid org_cd"):
        MoisOrganizationCodeConnector.parse_organizations(document)


def test_parser_rejects_abolished_row_in_current_only_contract() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload([organization_row(stop_selt="1", cls_de="20260101")])
        ),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(MoisOrganizationCodeApiError, match="current rows only"):
        connector.parse_organizations(document)


def test_parser_rejects_duplicate_org_code() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload(
                [
                    organization_row(),
                    organization_row(full_nm="행정안전부 변경표현"),
                ]
            )
        ),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(MoisOrganizationCodeApiError, match="duplicate org_cd"):
        connector.parse_organizations(document)

def test_provider_error_fails_closed() -> None:
    payload = {
        "response": {
            "header": {"resultCode": "20", "resultMsg": "PERMISSION_DENIED"},
            "body": {},
        }
    }
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(payload),
    )
    with pytest.raises(MoisOrganizationCodeApiError, match="returned 20"):
        connector.fetch(connector.discover()[0])


def test_invalid_lifecycle_date_fails_closed() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload([organization_row(chg_de="20260231")])
        ),
    )
    document = connector.fetch(connector.discover()[0])
    with pytest.raises(MoisOrganizationCodeApiError, match="invalid chg_de"):
        connector.parse_organizations(document)


def test_constructor_rejects_invalid_org_code_filter() -> None:
    with pytest.raises(ValueError, match="seven-digit"):
        MoisOrganizationCodeConnector(org_code="123")


def test_malformed_row_list_fails_closed() -> None:
    payload = response_payload([organization_row()])
    payload["response"]["body"]["items"] = {"item": [organization_row(), "bad-row"]}
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(payload),
    )
    with pytest.raises(MoisOrganizationCodeApiError, match="malformed row"):
        connector.fetch(connector.discover()[0])


def test_invalid_pagination_metadata_fails_closed() -> None:
    payload = response_payload([organization_row()])
    payload["response"]["body"]["totalCount"] = "not-an-int"
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(payload),
    )
    with pytest.raises(MoisOrganizationCodeApiError, match="invalid totalCount"):
        connector.fetch(connector.discover()[0])
