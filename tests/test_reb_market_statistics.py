"""Only synthetic provider-shaped R-ONE data. Do not assert sample is full coverage."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from packages.connectors.reb_market_statistics import (
    HOUSING_TABLE,
    REGION_CODE_NAMESPACE,
    SCOPE_LIMIT,
    RebMarketStatError,
    parse_reb_housing_research_page,
)
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyDenied


def _policy() -> SourcePolicy:
    # A disposable research fixture, NOT an applied canonical SourcePolicy approval.
    return SourcePolicy(
        id=UUID("16130000-0000-0000-0000-000000000005"),
        domain="www.reb.or.kr",
        source_class="official_statistic_research_only",
        collection_mode=SourceCollectionMode.API,
        can_fetch=False,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=datetime(2026, 10, 10, tzinfo=UTC),
        license=None,
        policy_note="Offline L1 research response sample; no live API approval or publication.",
    )


def _row(**updates: object) -> dict[str, object]:
    row: dict[str, object] = {
        "STATBL_ID": HOUSING_TABLE,
        "DTACYCLE_CD": "MM",
        "WRTTIME_IDTFR_ID": "202609",
        "CLS_ID": "500001",
        "CLS_NM": "전국",
        "ITM_ID": "100001",
        "ITM_NM": "동(호)수",
        "DTA_VAL": "12,345",
        "UI_NM": "동(호)수",
        "GRP_FULLNM": "IGNORE",
        "WRTTIME_DESC": "2026년 9월",
        "unknown_external_fulltext": "MUST_NOT_RETAIN",
    }
    row.update(updates)
    return row


def _response(*rows: dict[str, object], total: int = 137976, status: str = "INFO-000"):
    return {
        "SttsApiTblData": [
            {
                "head": [
                    {"list_total_count": total},
                    {"RESULT": {"CODE": status, "MESSAGE": "정상 처리되었습니다."}},
                ]
            },
            {"row": list(rows)},
        ]
    }


def _parse(resp: dict | None = None):
    return parse_reb_housing_research_page(
        resp if resp is not None else _response(_row()),
        policy=_policy(),
    )


def test_official_sample_is_expressly_not_complete_or_publishable():
    result = _parse()
    assert result.source_url.endswith("/A_2024_00546.do")
    assert result.provider_total_count == 137976
    assert result.sampled_row_count == 1
    assert result.coverage == SCOPE_LIMIT
    assert result.publishable is False
    row = result.rows[0]
    assert row.month == "202609"
    assert row.region_code == "500001"
    assert row.region_label == "전국"
    assert row.reported_housing_units == 12345
    assert row.region_code_namespace == REGION_CODE_NAMESPACE
    assert not any(k in repr(result) for k in ("MUST_NOT_RETAIN", "GRP_FULLNM", "WRTTIME_DESC"))
    assert not hasattr(result, "person_id")
    assert not hasattr(row, "lawd_cd")


def test_real_sample_shape_multiple_unique_regions_stays_incomplete():
    p = _parse(
        _response(
            _row(),
            _row(CLS_ID=510029, CLS_NM="서울특별시", DTA_VAL="999"),
            total=137976,
        )
    )
    assert len(p.rows) == 2
    assert p.rows[1].reported_housing_units == 999
    assert p.publishable is False


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("STATBL_ID", "A_MADE_UP"),
        ("DTACYCLE_CD", "YY"),
        ("ITM_ID", "100002"),
        ("ITM_NM", "㎡"),
        ("UI_NM", "필지"),
        ("WRTTIME_IDTFR_ID", "202613"),
        ("WRTTIME_IDTFR_ID", "202600"),
        ("WRTTIME_IDTFR_ID", "20260901"),
        ("CLS_ID", "11110"),  # MOLIT LAWD_CD is NOT R-ONE CLS_ID.
        ("CLS_NM", "서울 강남구 101동 1203호"),
        ("DTA_VAL", "-5"),
        ("DTA_VAL", "1.3"),
        ("DTA_VAL", "1,2"),
    ],
)
def test_unverified_scope_unit_date_or_value_rejected(field, bad):
    with pytest.raises(RebMarketStatError):
        _parse(_response(_row(**{field: bad})))


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"SttsApiTblData": []},
        {"SttsApiTblData": [{"head": []}, {"row": []}]},
        {
            "SttsApiTblData": [
                {"head": [{"list_total_count": 0}, {"RESULT": {"CODE": "INFO-000"}}]},
                {"row": [_row()]},
            ]
        },
        {
            "SttsApiTblData": [
                {"head": [{"list_total_count": 5}, {"RESULT": {"CODE": "INFO-100"}}]},
                {"row": []},
            ]
        },
    ],
)
def test_response_envelope_error_rejected(bad):
    with pytest.raises(RebMarketStatError):
        _parse(bad)


def test_duplicate_month_region_rejected():
    with pytest.raises(RebMarketStatError, match="duplicated"):
        _parse(_response(_row(), _row(DTA_VAL="12,346")))


def test_unknown_table_and_per_region_coverage_are_not_upgraded():
    value = _parse(_response(_row(), total=1))
    assert (
        value.publishable is False
    )  # Even if page count equals total, no historical completeness.
    assert value.coverage == SCOPE_LIMIT


def test_policy_prohibits_fetch_fulltext_ai_and_wrong_domain():
    for patch in (
        {"domain": "apis.data.go.kr"},
        {"can_fetch": True},
        {"can_store_fulltext": True},
        {"can_send_to_ai": True},
        {"can_show_excerpt": True},
        {"can_store_metadata": False},
        {"collection_mode": SourceCollectionMode.HTTP},
    ):
        with pytest.raises(PolicyDenied):
            parse_reb_housing_research_page(
                _response(_row()), policy=_policy().model_copy(update=patch)
            )
