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
from packages.connectors.nec_local_elections import nec_local_election_policy
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
    with pytest.raises(ValueError, match="seven uppercase alphanumeric characters"):
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

def test_current_provider_stan_org_cd_envelope_is_supported() -> None:
    payload = {
        "StanOrgCd": [
            {
                "head": [
                    {"totalCount": 1},
                    {"numOfRows": 1, "pageNo": 1, "type": "JSON"},
                    {"RESULT": {"resultCode": "INFO-0", "resultMsg": "NOMAL SERVICE"}},
                ]
            },
            {"row": [organization_row()]},
        ]
    }
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(payload),
        page_size=1,
    )

    document = connector.fetch(connector.discover()[0])
    records = connector.parse_organizations(document)

    assert len(records) == 1
    assert records[0].org_code == "1741000"
    assert document.metadata["total_count"] == "1"
    assert document.metadata["provider_page_no"] == "1"
    assert document.metadata["provider_page_size"] == "1"
    assert document.metadata["result_code"] == "INFO-0"

def test_encoded_data_go_key_is_decoded_once_before_request() -> None:
    encoded = "abc%2Bdef%2Fghi%3D"
    decoded = "abc+def/ghi="

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["ServiceKey"] == decoded
        return httpx.Response(200, json=response_payload([organization_row()]))

    connector = MoisOrganizationCodeConnector(
        api_key=encoded,
        transport=httpx.MockTransport(handler),
    )
    records = connector.parse_organizations(connector.fetch(connector.discover()[0]))
    assert len(records) == 1

def test_mois_and_nec_share_one_host_level_data_go_policy() -> None:
    mois = mois_organization_code_policy()
    nec = nec_local_election_policy()

    assert mois == nec
    assert mois.id == nec.id
    assert "15077870" in (mois.policy_note or "")
    assert "15000908" in (mois.policy_note or "")


def test_d_prefixed_provider_org_codes_are_valid_source_keys() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        org_code="D194185",
        transport=transport_for(
            response_payload(
                [
                    organization_row(
                        org_cd="D194185",
                        high_cd="D194185",
                        highst_cd="D194185",
                        rep_cd="D194185",
                    )
                ]
            )
        ),
    )
    document = connector.fetch(connector.discover()[0])
    records = connector.parse_organizations(document)

    assert records[0].org_code == "D194185"
    assert records[0].parent_org_code == "D194185"
    assert records[0].top_org_code == "D194185"
    assert records[0].representative_org_code == "D194185"


@pytest.mark.parametrize(
    "value",
    ["1741000", "B555544", "C123456", "D194185", "P123456", "1Z00189"],
)
def test_current_provider_org_code_namespace_is_accepted(value: str) -> None:
    connector = MoisOrganizationCodeConnector(org_code=value)
    assert httpx.URL(connector.discover()[0]).params["org_cd"] == value


@pytest.mark.parametrize("value", ["b555544", "A-12345", "123456", "12345678", "기관코드1"])
def test_unreviewed_org_code_shapes_fail_closed(value: str) -> None:
    with pytest.raises(ValueError):
        MoisOrganizationCodeConnector(org_code=value)

@pytest.mark.parametrize("raw_value", ["1988. 1.", "1988. 12."])
def test_inexact_legacy_created_date_preserves_raw_text_without_inventing_day(
    raw_value: str,
) -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload([organization_row(crt_de=raw_value)])
        ),
    )
    document = connector.fetch(connector.discover()[0])
    record = connector.parse_organizations(document)[0]

    assert record.created_date is None
    assert record.created_date_text == raw_value

@pytest.mark.parametrize("raw_value", ["19660900", "19901131"])
def test_live_invalid_calendar_created_dates_preserve_raw_text(raw_value: str) -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload([organization_row(crt_de=raw_value)])
        ),
    )
    document = connector.fetch(connector.discover()[0])
    record = connector.parse_organizations(document)[0]

    assert record.created_date is None
    assert record.created_date_text == raw_value


@pytest.mark.parametrize("raw_value", ["1988. 13.", "not-a-date"])
def test_other_invalid_created_dates_fail_closed(raw_value: str) -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        transport=transport_for(
            response_payload([organization_row(crt_de=raw_value)])
        ),
    )
    document = connector.fetch(connector.discover()[0])

    with pytest.raises(MoisOrganizationCodeApiError, match="invalid crt_de"):
        connector.parse_organizations(document)

def test_for_page_preserves_connector_scope_without_mutation() -> None:
    connector = MoisOrganizationCodeConnector(
        api_key=SECRET,
        page_no=1,
        page_size=1000,
    )
    page = connector.for_page(2)

    assert connector.page_no == 1
    assert page.page_no == 2
    assert page.page_size == 1000
    assert page.full_name is None
    assert page.org_code is None
