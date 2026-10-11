"""Official R-ONE housing transaction statistics, offline research-page normalization.

Distinct from MOLIT contract-date raw transactions and from personal asset disclosures.
The no-key R-ONE response is a tiny provider sample, never publishable market coverage.
No fetch, credential, canonical DB, person linkage or SourcePolicy registration exists here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

PROVIDER_DOMAIN = "www.reb.or.kr"
HOUSING_TABLE = "A_2024_00546"
HOUSING_SOURCE = "https://www.reb.or.kr/r-one/portal/stat/easyStatPage/A_2024_00546.do"
HOUSING_ENDPOINT = "https://www.reb.or.kr/r-one/openapi/SttsApiTblData.do"
L2_POLICY_ID = UUID("16130000-0000-0000-0000-000000000007")
L2_SOURCE_CONTRACT = "reb_housing_month_reporting_date_l2_v1"
L2_REGION = "500001"  # Nationwide official R-ONE CLS_ID, NOT MOLIT LAWD_CD
L2_SEOUL_REGION = "500002"  # Verified official Seoul CLS_ID on both sale tables
L2_SALE_REGIONS = {L2_REGION: "전국", L2_SEOUL_REGION: "서울"}
SOURCE_KIND = "REB_REPORTED_DATE_ALL_HOUSING_TRADES"

# IDs and item names observed in the official R-ONE StatsVisual dashboard
# and selectOpenApiItmCd source-code endpoint, 2026-10-10.
# No inferred market prices, individual purchases or geographical joins.
REGIONAL_SALE_TABLES = {
    "apartment_sale": {
        "statbl_id": "A_2024_00554",
        "table_title": "(월) 행정구역별 아파트매매거래현황",
        "item_id": "100001",
        "item_name": "동(호)수",
        "unit": "호수",
    },
    "land_sale": {
        "statbl_id": "A_2024_00536",
        "table_title": "(월) 행정구역별 토지매매거래현황",
        "item_id": "100001",
        "item_name": "필지수",
        "unit": "필지수",
    },
}

SCOPE_LIMIT = "UNVERIFIED_PROVIDER_SAMPLE_OR_SINGLE_PAGE"
REGION_CODE_NAMESPACE = "RONE_CLS_ID_NOT_MOLIT_LAWD_CD"
_COUNT = re.compile(r"^(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)$")
_SIX_DIGITS = re.compile(r"^[0-9]{6}$")


@dataclass(frozen=True)
class RebRegionalSaleRow:
    kind: str
    month: str
    region_code: str  # Official R-ONE CLS_ID, never MOLIT LAWD_CD
    region_label: str
    count: int


@dataclass(frozen=True)
class RebRegionalSalesPage:
    kind: str
    month: str
    provider_total_count: int
    sampled_row_count: int
    rows: tuple[RebRegionalSaleRow, ...]
    completeness: str = "QUERY_PAGE_ONLY_OFFICIAL_REVISION_UNKNOWN"
    publishable: bool = False


class RebMarketStatError(ValueError):
    """R-ONE envelope, scope, data definition or partiality cannot be trusted."""


@dataclass(frozen=True)
class RebHousingVolume:
    month: str
    region_code: str
    region_label: str
    reported_housing_units: int
    source_table: str = HOUSING_TABLE
    source_kind: str = SOURCE_KIND
    region_code_namespace: str = REGION_CODE_NAMESPACE


@dataclass(frozen=True)
class RebHousingResearchPage:
    provider_total_count: int
    sampled_row_count: int
    rows: tuple[RebHousingVolume, ...]
    source_url: str = HOUSING_SOURCE
    coverage: str = SCOPE_LIMIT

    @property
    def publishable(self) -> bool:
        """Even a full-looking sample does not prove the provider's universe."""
        return False


def _count(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise RebMarketStatError(f"{label} is not an unsigned integer")
    if isinstance(value, int):
        result = value
    elif isinstance(value, str) and _COUNT.fullmatch(value):
        result = int(value.replace(",", ""))
    else:
        raise RebMarketStatError(f"{label} is not an unsigned integer")
    if not 0 <= result <= 1_000_000_000:
        raise RebMarketStatError(f"{label} is outside bounded range")
    return result


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip() or len(value) > 150:
        raise RebMarketStatError(f"R-ONE {field} is missing or malformed")
    return value.strip()


def reb_market_l2_policy() -> SourcePolicy:
    """Single canonical domain SourcePolicy for reviewed local R-ONE market L2 calls.

    This object is NOT authority to alter a production SourcePolicy or publish data.
    """
    return SourcePolicy(
        id=L2_POLICY_ID,
        domain=PROVIDER_DOMAIN,
        source_class="official_reb_reported_date_housing_and_sales_api_l2",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=datetime(2026, 10, 10, tzinfo=UTC),
        license="Public-data portal 15134761: 이용허락범위 제한 없음; operation approval separately required",
        rate_limit=(
            "Local only: housing national, apartment/land sale national or Seoul, "
            "one table/region/month/row per request; no schedule or bulk scan"
        ),
        policy_note=(
            "Reviewed against R-ONE official Open API developer guide and data.go.kr 15134761. "
            "This object is an exact local-use source contract, not proof of owner review. "
            "Only A_2024_00546 (all-housing volume), A_2024_00554 (apartment sale "
            "volume) and A_2024_00536 (land sale parcels), ITM_ID=100001, "
            "CLS_ID=500001 for all housing and either 500001 or 500002 for "
            "apartment/land sales; one reporting month per research pull, "
            "metadata-only isolated SourceSnapshot/Observation. No production policy "
            "installation, public-map statistics, fulltext, AI, or Person links."
        ),
    )


def require_reb_market_l2_policy(policy: SourcePolicy) -> None:
    """Pin full source-rights policy for all reviewed R-ONE L2 source kinds."""
    require_policy(policy, PolicyAction.FETCH)
    require_policy(policy, PolicyAction.STORE_METADATA)
    if policy.model_dump(mode="json") != reb_market_l2_policy().model_dump(mode="json"):
        raise PolicyDenied("R-ONE L2 requires the exact reviewed single-month policy")


def parse_reb_housing_l2_month(
    response: Mapping[str, Any],
    *,
    month: str,
    region_code: str,
    policy: SourcePolicy,
) -> RebHousingResearchPage:
    """Validate one exact authenticated 1-row/month slice; still never publishable."""
    require_reb_market_l2_policy(policy)
    if not _SIX_DIGITS.fullmatch(month) or region_code != L2_REGION:
        raise RebMarketStatError("L2 permits only one reporting month and national region code")
    try:
        date(int(month[:4]), int(month[4:]), 1)
    except ValueError:
        raise RebMarketStatError("invalid L2 requested month") from None
    page = _parse_reb_housing_response(response)
    if (
        page.provider_total_count != 1
        or page.sampled_row_count != 1
        or page.rows[0].month != month
        or page.rows[0].region_code != region_code
    ):
        raise RebMarketStatError("R-ONE L2 response does not match one exact month/region")
    return page


def _scope_policy(policy: SourcePolicy) -> None:
    require_policy(policy, PolicyAction.STORE_METADATA)
    if (
        policy.domain != PROVIDER_DOMAIN
        or policy.collection_mode != SourceCollectionMode.API
        or policy.can_fetch
        or policy.can_store_fulltext
        or policy.can_send_to_ai
        or policy.can_show_excerpt
    ):
        raise PolicyDenied("R-ONE research page accepts offline metadata-only policy only")


def parse_reb_housing_research_page(
    response: Mapping[str, Any], *, policy: SourcePolicy
) -> RebHousingResearchPage:
    """Parse supplied official JSON without claiming L2, source freshness or completeness.

    R-ONE requires an issued KEY to enumerate beyond its fixed keyless sample.
    """
    _scope_policy(policy)
    return _parse_reb_housing_response(response)


def _parse_reb_housing_response(response: Mapping[str, Any]) -> RebHousingResearchPage:
    if not isinstance(response, Mapping) or set(response) != {"SttsApiTblData"}:
        raise RebMarketStatError("unexpected R-ONE response family")
    sections = response["SttsApiTblData"]
    if (
        not isinstance(sections, list)
        or len(sections) != 2
        or not all(isinstance(section, Mapping) for section in sections)
    ):
        raise RebMarketStatError("malformed R-ONE envelope sections")
    head, body = sections
    if set(head) != {"head"} or set(body) != {"row"}:
        raise RebMarketStatError("R-ONE head/row sections missing or reordered")
    headers, rows = head["head"], body["row"]
    if (
        not isinstance(headers, list)
        or len(headers) != 2
        or not all(isinstance(h, Mapping) for h in headers)
    ):
        raise RebMarketStatError("R-ONE provider header is incomplete")
    first, second = headers
    if set(first) != {"list_total_count"} or set(second) != {"RESULT"}:
        raise RebMarketStatError("R-ONE metadata format changed")
    status = second["RESULT"]
    if not isinstance(status, Mapping) or status.get("CODE") != "INFO-000":
        raise RebMarketStatError("R-ONE provider did not report success")
    total = _count(first["list_total_count"], "list_total_count")
    if not isinstance(rows, list) or len(rows) > 1000 or len(rows) > total:
        raise RebMarketStatError("R-ONE row count exceeds bounded declared scope")
    normalized: list[RebHousingVolume] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise RebMarketStatError("R-ONE row is malformed")
        if (
            row.get("STATBL_ID") != HOUSING_TABLE
            or row.get("DTACYCLE_CD") != "MM"
            or str(row.get("ITM_ID")) != "100001"
            or row.get("ITM_NM") != "동(호)수"
            or row.get("UI_NM") != "동(호)수"
        ):
            raise RebMarketStatError("R-ONE table/item/unit is not verified housing trade volume")
        month = _required_text(row, "WRTTIME_IDTFR_ID")
        if not _SIX_DIGITS.fullmatch(month):
            raise RebMarketStatError("R-ONE reporting month must use YYYYMM")
        try:
            date(int(month[:4]), int(month[4:]), 1)
        except ValueError:
            raise RebMarketStatError("invalid official reporting month") from None
        code = str(row.get("CLS_ID", ""))
        if not _SIX_DIGITS.fullmatch(code):
            raise RebMarketStatError("R-ONE CLS_ID must be six-digit provider namespace")
        label = _required_text(row, "CLS_NM")
        if not re.fullmatch(r"[가-힣· ()-]{1,60}", label):
            raise RebMarketStatError("R-ONE aggregate region label malformed")
        key = (month, code)
        if key in seen:
            raise RebMarketStatError("duplicated provider region/month row")
        seen.add(key)
        normalized.append(
            RebHousingVolume(
                month=month,
                region_code=code,
                region_label=label,
                reported_housing_units=_count(row.get("DTA_VAL"), "DTA_VAL"),
            )
        )
    return RebHousingResearchPage(
        provider_total_count=total,
        sampled_row_count=len(normalized),
        rows=tuple(normalized),
    )


def parse_reb_sale_month(
    response: Mapping[str, Any],
    *,
    kind: str,
    month: str,
    region_code: str = L2_REGION,
    policy: SourcePolicy,
) -> RebRegionalSalesPage:
    """Validate exactly one provider-approved national/Seoul sale month, nonpublishable."""
    require_reb_market_l2_policy(policy)
    if kind not in REGIONAL_SALE_TABLES:
        raise RebMarketStatError("R-ONE sale table is outside reviewed catalog")
    if region_code not in L2_SALE_REGIONS:
        raise RebMarketStatError("R-ONE sale region is outside reviewed pilot scope")
    if not isinstance(month, str) or not _SIX_DIGITS.fullmatch(month):
        raise RebMarketStatError("R-ONE reporting month must be YYYYMM")
    try:
        date(int(month[:4]), int(month[4:]), 1)
    except ValueError:
        raise RebMarketStatError("invalid reporting month") from None
    if not isinstance(response, Mapping) or set(response) != {"SttsApiTblData"}:
        raise RebMarketStatError("R-ONE sale response envelope changed or returned an error")
    sections = response["SttsApiTblData"]
    if not isinstance(sections, list) or len(sections) != 2:
        raise RebMarketStatError("R-ONE response is not a single table page")
    header, body = sections
    if not isinstance(header, Mapping) or not isinstance(body, Mapping):
        raise RebMarketStatError("R-ONE sale response head/row objects missing")
    if set(header) != {"head"} or set(body) != {"row"}:
        raise RebMarketStatError("R-ONE sale response fields are not the reviewed format")
    heads = header["head"]
    if not isinstance(heads, list) or len(heads) != 2:
        raise RebMarketStatError("R-ONE sale provider metadata changed")
    if any(not isinstance(obj, Mapping) for obj in heads):
        raise RebMarketStatError("R-ONE sale provider metadata invalid")
    if set(heads[0]) != {"list_total_count"} or set(heads[1]) != {"RESULT"}:
        raise RebMarketStatError("R-ONE sale provider metadata format changed")
    result = heads[1]["RESULT"]
    if not isinstance(result, Mapping) or result.get("CODE") != "INFO-000":
        raise RebMarketStatError("R-ONE sale provider did not report success")
    total = _count(heads[0]["list_total_count"], "list_total_count")
    rows = body["row"]
    if total != 1 or not isinstance(rows, list) or len(rows) != 1:
        raise RebMarketStatError("R-ONE sale request scope is incomplete or ambiguous")
    row = rows[0]
    expected = REGIONAL_SALE_TABLES[kind]
    if not isinstance(row, Mapping) or any(
        (
            row.get("STATBL_ID") != expected["statbl_id"],
            row.get("DTACYCLE_CD") != "MM",
            row.get("WRTTIME_IDTFR_ID") != month,
            str(row.get("CLS_ID")) != region_code,
            str(row.get("ITM_ID")) != expected["item_id"],
            row.get("ITM_NM") != expected["item_name"],
            row.get("UI_NM") != expected["unit"],
        )
    ):
        raise RebMarketStatError("R-ONE sale row does not match approved table/item/month/region")
    label = _required_text(row, "CLS_NM")
    if label != L2_SALE_REGIONS[region_code]:
        raise RebMarketStatError("R-ONE official region label mismatches pilot selection")
    return RebRegionalSalesPage(
        kind=kind,
        month=month,
        provider_total_count=total,
        sampled_row_count=1,
        rows=(
            RebRegionalSaleRow(
                kind=kind,
                month=month,
                region_code=region_code,
                region_label=label,
                count=_count(row.get("DTA_VAL"), "DTA_VAL"),
            ),
        ),
    )
