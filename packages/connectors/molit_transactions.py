"""Bounded MOLIT apartment/land sale data as *regional market context*, not ownership.

Official catalog datasets 15126469 (apartment sales) and 15126466 (land sales).
Provider responses contain parcel/unit fields that MUST NOT enter normalized records.
This source-specific adapter does not persist, create Person associations, or publish.
The data.go.kr host policy alone does not authorize these two dataset endpoints.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, TypedDict

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode
from packages.verification.policy import PolicyAction, PolicyDenied, require_policy

from .data_go_kr import POLICY_ID as DATA_GO_KR_POLICY_ID

TradeKind = Literal["apartment", "land"]
# Explicit reviewed, effective SourcePolicy scope must be registered before any live fetch.
MOLIT_POLICY_SCOPE = "MOLIT_APPROVED_DATASETS_15126469_15126466"
PROVIDER = "apis.data.go.kr"


class _Dataset(TypedDict):
    catalog: str
    area_fields: tuple[str, ...]


DATASETS: dict[str, _Dataset] = {
    "apartment": {
        "catalog": "https://www.data.go.kr/data/15126469/openapi.do",
        "area_fields": ("excluUseAr", "전용면적"),
    },
    "land": {
        "catalog": "https://www.data.go.kr/data/15126466/openapi.do",
        "area_fields": ("dealArea", "거래면적"),
    },
}
_PRICE_FIELDS = ("dealAmount", "거래금액")
_YEAR_FIELDS = ("dealYear", "년")
_MONTH_FIELDS = ("dealMonth", "월")
_DAY_FIELDS = ("dealDay", "일")
_CANCEL_FIELDS = ("cdealType", "해제여부")
_INT = re.compile(r"^(?:\d+|[1-9]\d{0,2}(?:,\d{3})+)$")
_DECIMAL = re.compile(r"^\d+(?:\.\d+)?$")
_LAWD = re.compile(r"^\d{5}$")
_YM = re.compile(r"^\d{6}$")
_XML_LIMIT = 3_000_000


class MolitTradeError(ValueError):
    """Official response, policy, scope, or completeness cannot be proved."""


@dataclass(frozen=True)
class _Trade:
    # Ephemeral numeric fields only. Never add parcel, apartment building, floor or person.
    value_10k_krw: int
    cancelled: bool


@dataclass(frozen=True)
class MolitTradePage:
    kind: TradeKind
    lawd_cd: str
    deal_ymd: str
    page_no: int
    page_size: int
    provider_total_count: int
    rows: tuple[_Trade, ...]


@dataclass(frozen=True)
class MolitMarketSummary:
    kind: TradeKind
    lawd_cd: str
    deal_ymd: str
    reported_count: int
    active_count: int
    cancelled_count: int
    median_active_price_10k_krw: Decimal | None
    catalog_url: str
    completeness: str = "QUERY_PAGE_COUNTS_RECONCILED_NOT_DEDUPLICATED"
    source_revision_status: str = "PROVIDER_CORRECTION_HISTORY_UNKNOWN"
    person_linkage: str = "NONE_NOT_OWNERSHIP_EVIDENCE"

    def as_regional_metadata(self) -> dict[str, str | int | None]:
        """Sanitized source metadata; still needs canonical evidence/publication review."""
        return {
            "kind": self.kind,
            "lawd_cd": self.lawd_cd,
            "deal_ymd": self.deal_ymd,
            "reported_count": self.reported_count,
            "active_count": self.active_count,
            "cancelled_count": self.cancelled_count,
            "median_active_price_10k_krw": (
                str(self.median_active_price_10k_krw)
                if self.median_active_price_10k_krw is not None
                else None
            ),
            "catalog_url": self.catalog_url,
            "completeness": self.completeness,
            "source_revision_status": self.source_revision_status,
            "person_linkage": self.person_linkage,
        }


def validate_scope(kind: str, lawd_cd: str, deal_ymd: str, page_size: int) -> None:
    if kind not in DATASETS:
        raise MolitTradeError("unsupported official MOLIT dataset")
    if not isinstance(lawd_cd, str) or not _LAWD.fullmatch(lawd_cd) or lawd_cd == "00000":
        raise MolitTradeError("LAWD_CD must be exactly five official region digits")
    if not isinstance(deal_ymd, str) or not _YM.fullmatch(deal_ymd):
        raise MolitTradeError("DEAL_YMD must be YYYYMM")
    year, month = int(deal_ymd[:4]), int(deal_ymd[4:])
    if not 2000 <= year <= 2099 or not 1 <= month <= 12:
        raise MolitTradeError("DEAL_YMD is outside valid calendar month")
    if isinstance(page_size, bool) or not isinstance(page_size, int) or not 1 <= page_size <= 1000:
        raise MolitTradeError("page size must be in 1..1000")


def require_molit_policy(policy: SourcePolicy) -> None:
    """The shared data.go.kr host policy alone never grants new dataset authority."""
    require_policy(policy, PolicyAction.STORE_METADATA)
    if (
        policy.id != DATA_GO_KR_POLICY_ID
        or policy.domain != PROVIDER
        or policy.collection_mode != SourceCollectionMode.API
        or MOLIT_POLICY_SCOPE not in (policy.policy_note or "").split()
        or policy.can_store_fulltext
        or policy.can_show_excerpt
        or policy.can_send_to_ai
    ):
        raise PolicyDenied("MOLIT endpoints require a reviewed, metadata-only source scope")


def _single(parent: ET.Element, aliases: tuple[str, ...], *, required: bool) -> str:
    matches = [child.text.strip() if child.text else "" for child in parent if child.tag in aliases]
    if len(matches) > 1 or (required and (not matches or not matches[0])):
        raise MolitTradeError("MOLIT required row field missing or ambiguous")
    return matches[0] if matches else ""


def _number(value: str, *, positive: bool = False) -> int:
    if not _INT.fullmatch(value):
        raise MolitTradeError("MOLIT numeric field is malformed")
    number = int(value.replace(",", ""))
    if positive and not number:
        raise MolitTradeError("MOLIT transaction price must be positive")
    return number


def _area(value: str) -> Decimal:
    if not _DECIMAL.fullmatch(value):
        raise MolitTradeError("MOLIT area field is malformed")
    try:
        area = Decimal(value)
    except InvalidOperation:
        raise MolitTradeError("MOLIT area field is malformed") from None
    if not area.is_finite() or area <= 0:
        raise MolitTradeError("MOLIT area must be positive")
    return area


def _trade(row: ET.Element, *, kind: TradeKind, deal_ymd: str) -> _Trade:
    price = _number(_single(row, _PRICE_FIELDS, required=True), positive=True)
    _area(_single(row, DATASETS[kind]["area_fields"], required=True))
    year = _number(_single(row, _YEAR_FIELDS, required=True))
    month = _number(_single(row, _MONTH_FIELDS, required=True))
    day = _number(_single(row, _DAY_FIELDS, required=True))
    try:
        dealt_on = date(year, month, day)
    except ValueError:
        raise MolitTradeError("MOLIT transaction date is invalid") from None
    if dealt_on.strftime("%Y%m") != deal_ymd:
        raise MolitTradeError("MOLIT transaction is outside requested month")
    cancelled = _single(row, _CANCEL_FIELDS, required=False)
    if cancelled not in {"", "O"}:
        raise MolitTradeError("MOLIT cancellation code is unsupported")
    # Critically, no jibun, apartment names, exact locations, transaction IDs,
    # floors, seller/buyer categories, or intermediary contacts are retained.
    return _Trade(price, cancelled == "O")


def parse_molit_trade_page(
    xml_body: bytes,
    *,
    kind: TradeKind,
    lawd_cd: str,
    deal_ymd: str,
    requested_page: int,
    page_size: int,
    policy: SourcePolicy,
) -> MolitTradePage:
    """Fail-closed parsing of one official XML page into numbers only."""
    require_molit_policy(policy)
    validate_scope(kind, lawd_cd, deal_ymd, page_size)
    if (
        isinstance(requested_page, bool)
        or not isinstance(requested_page, int)
        or requested_page < 1
    ):
        raise MolitTradeError("page number must be positive")
    if not isinstance(xml_body, bytes) or not 1 <= len(xml_body) <= _XML_LIMIT:
        raise MolitTradeError("XML response is missing or exceeds bounded size")
    if b"<!DOCTYPE" in xml_body.upper() or b"<!ENTITY" in xml_body.upper():
        raise MolitTradeError("XML with DTD or entity declarations is not supported")
    try:
        root = ET.fromstring(xml_body)
    except ET.ParseError:
        raise MolitTradeError("malformed official MOLIT XML") from None
    if root.tag != "response":
        raise MolitTradeError("unexpected MOLIT envelope")
    header = root.find("header")
    body = root.find("body")
    if header is None or body is None:
        raise MolitTradeError("MOLIT header/body missing")
    code = _single(header, ("resultCode",), required=True)
    if code not in {"00", "000"}:
        raise MolitTradeError("MOLIT provider returned a non-success result")
    response_page = _number(_single(body, ("pageNo",), required=True))
    response_size = _number(_single(body, ("numOfRows",), required=True))
    total = _number(_single(body, ("totalCount",), required=True))
    if response_page != requested_page or response_size != page_size or total > 1_000_000:
        raise MolitTradeError("MOLIT pagination/total is inconsistent")
    items = body.find("items")
    if items is None:
        raise MolitTradeError("MOLIT items envelope missing")
    if any(child.tag != "item" for child in items):
        raise MolitTradeError("MOLIT contains unexpected items structure")
    rows = tuple(_trade(item, kind=kind, deal_ymd=deal_ymd) for item in items)
    if len(rows) > page_size or len(rows) > total:
        raise MolitTradeError("MOLIT returned more records than declared")
    if total == 0 and rows:
        raise MolitTradeError("zero total disagrees with items")
    return MolitTradePage(kind, lawd_cd, deal_ymd, requested_page, page_size, total, rows)


def summarize_molit_month(pages: list[MolitTradePage]) -> MolitMarketSummary:
    """Only complete same-scope pages can yield a displayable aggregate."""
    if not pages:
        raise MolitTradeError("no pages were supplied")
    first = pages[0]
    for page in pages:
        if (page.kind, page.lawd_cd, page.deal_ymd, page.page_size, page.provider_total_count) != (
            first.kind,
            first.lawd_cd,
            first.deal_ymd,
            first.page_size,
            first.provider_total_count,
        ):
            raise MolitTradeError("mixed source scope or provider-total revision")
    total = first.provider_total_count
    expected_pages = max(1, (total + first.page_size - 1) // first.page_size)
    if len(pages) != expected_pages or {p.page_no for p in pages} != set(
        range(1, expected_pages + 1)
    ):
        raise MolitTradeError("incomplete or duplicate MOLIT page coverage")
    if any(
        len(p.rows) != min(first.page_size, max(0, total - (p.page_no - 1) * first.page_size))
        for p in pages
    ):
        raise MolitTradeError("MOLIT page cardinality mismatch")
    all_rows = [r for page in sorted(pages, key=lambda p: p.page_no) for r in page.rows]
    active_prices = sorted(r.value_10k_krw for r in all_rows if not r.cancelled)
    active = len(active_prices)
    center = active // 2
    midpoint = (
        (
            Decimal(active_prices[center])
            if active % 2
            else (Decimal(active_prices[center - 1]) + Decimal(active_prices[center])) / 2
        )
        if active
        else None
    )
    result = MolitMarketSummary(
        kind=first.kind,
        lawd_cd=first.lawd_cd,
        deal_ymd=first.deal_ymd,
        reported_count=total,
        active_count=active,
        cancelled_count=total - active,
        median_active_price_10k_krw=midpoint,
        catalog_url=DATASETS[first.kind]["catalog"],
    )
    return result
