"""Deterministic offline contracts; no live provider calls or person associations."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal

import pytest

from packages.connectors.data_go_kr import data_go_kr_policy
from packages.connectors.molit_transactions import (
    DATASETS,
    MOLIT_POLICY_SCOPE,
    MolitMarketSummary,
    MolitTradeError,
    parse_molit_trade_page,
    summarize_molit_month,
)
from packages.verification.policy import PolicyDenied


def approved_policy():
    p = data_go_kr_policy()
    return p.model_copy(update={"policy_note": f"{p.policy_note} {MOLIT_POLICY_SCOPE}"})


def _xml(
    rows: list[dict[str, str]],
    *,
    page_no: int = 1,
    num_of_rows: int = 2,
    total: int | None = None,
    code: str = "00",
) -> bytes:
    from xml.sax.saxutils import escape

    def item(row: dict[str, str]) -> str:
        return "<item>" + "".join(f"<{k}>{escape(v)}</{k}>" for k, v in row.items()) + "</item>"

    contents = "".join(map(item, rows))
    return (
        f"<response><header><resultCode>{code}</resultCode></header><body>"
        f"<items>{contents}</items><numOfRows>{num_of_rows}</numOfRows>"
        f"<pageNo>{page_no}</pageNo><totalCount>{len(rows) if total is None else total}</totalCount>"
        "</body></response>"
    ).encode()


def _row(
    kind: str = "apartment",
    *,
    price: str = "120,000",
    cancel: str = "",
    day: str = "10",
) -> dict[str, str]:
    row = {
        "dealAmount": price,
        "dealYear": "2026",
        "dealMonth": "09",
        "dealDay": day,
        "cdealType": cancel,
        "jibun": "100-99",
        "buyerGbn": "PERSON",
        "slerGbn": "PERSON",
        "estateAgentSggNm": "PRIVATE_OTHER",
        "floor": "17",
    }
    if kind == "apartment":
        row["excluUseAr"] = "84.93"
        row["aptNm"] = "NOT_STORED_COMPLEX"
    else:
        row["dealArea"] = "298.8"
        row["landUse"] = "PRIVATE_EXACT_LOCATION"
    return row


def _page(
    kind: str = "apartment",
    *,
    xml: bytes | None = None,
    page_no: int = 1,
    page_size: int = 2,
    total: int | None = None,
):
    return parse_molit_trade_page(
        xml
        if xml is not None
        else _xml([_row(kind)], page_no=page_no, num_of_rows=page_size, total=total),
        kind=kind,
        lawd_cd="11110",
        deal_ymd="202609",
        requested_page=page_no,
        page_size=page_size,
        policy=approved_policy(),
    )


@pytest.mark.parametrize("kind", ["apartment", "land"])
def test_official_apt_and_land_pure_summary_drops_precise_fields(kind):
    p = _page(kind)
    summary = summarize_molit_month([p])
    assert isinstance(summary, MolitMarketSummary)
    assert summary.reported_count == summary.active_count == 1
    assert summary.cancelled_count == 0
    assert summary.median_active_price_10k_krw == Decimal(120000)
    assert summary.person_linkage == "NONE_NOT_OWNERSHIP_EVIDENCE"
    assert summary.completeness == "QUERY_PAGE_COUNTS_RECONCILED_NOT_DEDUPLICATED"
    assert summary.source_revision_status == "PROVIDER_CORRECTION_HISTORY_UNKNOWN"
    assert summary.catalog_url == DATASETS[kind]["catalog"]
    serialized = json.dumps(summary.as_regional_metadata(), ensure_ascii=False)
    for marker in (
        "100-99",
        "NOT_STORED_COMPLEX",
        "PRIVATE_",
        "aptNm",
        "jibun",
        "buyerGbn",
        "seller",
        "17층",
    ):
        assert marker not in serialized


def test_cancellation_kept_out_of_active_price_but_counted():
    p = _page(xml=_xml([_row(price="100,000"), _row(price="900,000", cancel="O")]))
    summary = summarize_molit_month([p])
    assert summary.reported_count == 2
    assert summary.active_count == 1
    assert summary.cancelled_count == 1
    assert summary.median_active_price_10k_krw == Decimal(100000)


def test_even_sample_price_median_keeps_exact_half_in_manwon():
    page = _page(xml=_xml([_row(price="90,000"), _row(price="90,001")]))
    summary = summarize_molit_month([page])
    assert summary.median_active_price_10k_krw == Decimal("90000.5")
    assert summary.as_regional_metadata()["median_active_price_10k_krw"] == "90000.5"


def test_private_fields_do_not_survive_even_on_in_memory_page():
    page = _page()
    rendered = repr(page)
    assert "100-99" not in rendered
    assert "NOT_STORED_COMPLEX" not in rendered
    assert "PRIVATE_OTHER" not in rendered
    assert "84.93" not in rendered


def test_cancelled_only_market_has_unknown_not_zero():
    p = _page(xml=_xml([_row(cancel="O")]))
    result = summarize_molit_month([p]).as_regional_metadata()
    assert result["active_count"] == 0
    assert result["median_active_price_10k_krw"] is None


def test_complete_two_page_month_with_exact_median():
    a = _page(xml=_xml([_row(price="100,000"), _row(price="123,001")], total=3))
    b = _page(xml=_xml([_row(price="122,000")], page_no=2, total=3), page_no=2)
    s = summarize_molit_month([b, a])
    assert (s.reported_count, s.active_count, s.cancelled_count) == (3, 3, 0)
    assert s.median_active_price_10k_krw == Decimal(122000)


@pytest.mark.parametrize(
    "case", ["missing_page", "duplicate_page", "drift_total", "wrong_page_len"]
)
def test_incomplete_or_inconsistent_pages_fail_closed(case):
    a = _page(xml=_xml([_row(), _row()], total=3))
    b = _page(xml=_xml([_row()], page_no=2, total=3), page_no=2)
    if case == "missing_page":
        pages = [a]
    elif case == "duplicate_page":
        pages = [a, a]
    elif case == "drift_total":
        pages = [a, replace(b, provider_total_count=4)]
    else:
        pages = [replace(a, rows=(a.rows[0],)), b]
    with pytest.raises(MolitTradeError):
        summarize_molit_month(pages)


@pytest.mark.parametrize(
    "badrow",
    [
        {"dealAmount": "-1"},
        {"dealAmount": "0"},
        {"dealAmount": "1,2"},
        {"excluUseAr": "0"},
        {"excluUseAr": "nan"},
        {"dealDay": "32"},
        {"dealMonth": "08"},
        {"cdealType": "UNCLEAR"},
    ],
)
def test_malformed_transaction_field_rejected(badrow):
    row = _row()
    row.update(badrow)
    with pytest.raises(MolitTradeError):
        _page(xml=_xml([row]))


@pytest.mark.parametrize(
    "badxml",
    [
        b"",
        b"<response>",
        b'<!DOCTYPE response [<!ENTITY local SYSTEM "file:///etc/passwd">]><response>&local;</response>',
        b"<response><header><resultCode>03</resultCode></header><body><items/></body></response>",
    ],
)
def test_invalid_xml_and_non_success_response_fail(badxml):
    with pytest.raises(MolitTradeError):
        _page(xml=badxml)


def test_invalid_source_query_or_pagination_rejected():
    with pytest.raises(MolitTradeError):
        _page(xml=_xml([_row()], page_no=2))
    with pytest.raises(MolitTradeError):
        parse_molit_trade_page(
            _xml([]),
            kind="apartment",
            lawd_cd="111100",
            deal_ymd="202609",
            requested_page=1,
            page_size=2,
            policy=approved_policy(),
        )
    with pytest.raises(MolitTradeError):
        parse_molit_trade_page(
            _xml([]),
            kind="land",
            lawd_cd="11110",
            deal_ymd="202613",
            requested_page=1,
            page_size=2,
            policy=approved_policy(),
        )


def test_host_policy_is_not_per_dataset_permission():
    with pytest.raises(PolicyDenied):
        parse_molit_trade_page(
            _xml([_row()]),
            kind="apartment",
            lawd_cd="11110",
            deal_ymd="202609",
            requested_page=1,
            page_size=2,
            policy=data_go_kr_policy(),
        )


def test_no_provider_row_identity_is_assumed_or_deduplicated():
    # Two identical disclosed market rows may be two trades; without a provider
    # row identifier their uniqueness cannot be asserted from this source.
    page = _page(xml=_xml([_row(), _row()]))
    market = summarize_molit_month([page]).as_regional_metadata()
    assert market["reported_count"] == 2
    assert market["active_count"] == 2
    assert "NOT_DEDUPLICATED" in str(market["completeness"])
    assert market["source_revision_status"] == "PROVIDER_CORRECTION_HISTORY_UNKNOWN"


def test_policy_marker_must_be_an_exact_token():
    fake = data_go_kr_policy().model_copy(update={"policy_note": "NOT_" + MOLIT_POLICY_SCOPE})
    with pytest.raises(PolicyDenied):
        parse_molit_trade_page(
            _xml([_row()]),
            kind="apartment",
            lawd_cd="11110",
            deal_ymd="202609",
            requested_page=1,
            page_size=2,
            policy=fake,
        )


def test_zero_rows_is_complete_empty_not_a_wealth_or_ownership_statement():
    p = _page(xml=_xml([], total=0))
    summary = summarize_molit_month([p])
    assert summary.reported_count == 0
    assert summary.active_count == 0
    assert summary.median_active_price_10k_krw is None
    assert summary.person_linkage == "NONE_NOT_OWNERSHIP_EVIDENCE"
