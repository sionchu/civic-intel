"""Official R-ONE housing transaction statistics, offline research-page normalization.

Distinct from MOLIT contract-date raw transactions and from personal asset disclosures.
The no-key R-ONE response is a tiny provider sample, never publishable market coverage.
No fetch, credential, canonical DB, person linkage or SourcePolicy registration exists here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

PROVIDER_DOMAIN = "www.reb.or.kr"
HOUSING_TABLE = "A_2024_00546"
HOUSING_SOURCE = "https://www.reb.or.kr/r-one/portal/stat/easyStatPage/A_2024_00546.do"
SOURCE_KIND = "REB_REPORTED_DATE_ALL_HOUSING_TRADES"
SCOPE_LIMIT = "UNVERIFIED_PROVIDER_SAMPLE_OR_SINGLE_PAGE"
REGION_CODE_NAMESPACE = "RONE_CLS_ID_NOT_MOLIT_LAWD_CD"
_COUNT = re.compile(r"^(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)$")
_SIX_DIGITS = re.compile(r"^[0-9]{6}$")


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
