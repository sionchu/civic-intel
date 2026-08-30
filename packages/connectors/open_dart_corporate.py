from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class DartApiError(RuntimeError):
    pass


class MissingDartApiKey(DartApiError):
    pass


class DartCorporateDataset(StrEnum):
    EXECUTIVE_STATUS = "EXECUTIVE_STATUS"
    DIRECTOR_COMPENSATION_V2 = "DIRECTOR_COMPENSATION_V2"
    TOP_COMPENSATION_V2 = "TOP_COMPENSATION_V2"
    OFFICER_MAJOR_HOLDER_OWNERSHIP = "OFFICER_MAJOR_HOLDER_OWNERSHIP"


POLICY_ID = UUID("17000000-0000-0000-0000-000000000001")


def open_dart_corporate_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="opendart.fss.or.kr",
        source_class="official_statutory_disclosure_api",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="OpenDART API terms apply; public-data/copyright rules govern reuse",
        rate_limit="Provider-controlled; general guide notes request-limit errors around 20,000 requests",
        policy_note=(
            "Reviewed 2026-08-30 against OpenDART terms and official executive-status, "
            "individual-compensation V2, top-compensation V2, and officer/major-holder "
            "ownership APIs. V0 stores normalized disclosure metadata only. Commercial reuse "
            "remains fail-closed pending product-use review."
        ),
    )


_ENDPOINTS = {
    DartCorporateDataset.EXECUTIVE_STATUS: "/api/exctvSttus.json",
    DartCorporateDataset.DIRECTOR_COMPENSATION_V2: "/api/hmvAuditIndvdlBySttusV2.json",
    DartCorporateDataset.TOP_COMPENSATION_V2: "/api/indvdlByPayV2.json",
    DartCorporateDataset.OFFICER_MAJOR_HOLDER_OWNERSHIP: "/api/elestock.json",
}

_REPORT_DATASETS = {
    DartCorporateDataset.EXECUTIVE_STATUS,
    DartCorporateDataset.DIRECTOR_COMPENSATION_V2,
    DartCorporateDataset.TOP_COMPENSATION_V2,
}

_REPORT_CODES = frozenset({"11011", "11012", "11013", "11014"})
_EMPTY_MARKERS = frozenset({"", "-", "해당사항없음", "해당 없음"})


@dataclass(frozen=True)
class DartExecutiveRecord:
    receipt_no: str
    corp_code: str
    corp_name: str
    name: str
    birth_year_month: str | None
    position: str | None
    registered_status: str | None
    full_time_status: str | None
    responsibility: str | None
    reported_main_career: str | None
    largest_shareholder_relation: str | None
    tenure_text: str | None
    tenure_end_on: date | None
    settlement_date: date


@dataclass(frozen=True)
class DartCompensationRecord:
    receipt_no: str
    corp_code: str
    corp_name: str
    name: str
    position: str | None
    fiscal_year_label: str | None
    compensation_total_krw: int
    settlement_date: date
    dataset: DartCorporateDataset


@dataclass(frozen=True)
class DartOwnershipRecord:
    receipt_no: str
    receipt_date: date
    corp_code: str
    corp_name: str
    reporter_name: str
    executive_registered_status: str | None
    executive_position: str | None
    major_shareholder_relation: str | None
    security_count: int | None
    security_change_count: int | None
    security_rate: float | None
    security_change_rate: float | None

    @property
    def public_person_scope(self) -> bool:
        return bool(self.executive_registered_status or self.major_shareholder_relation)


class OpenDartCorporateConnector(Connector):
    HOST = "opendart.fss.or.kr"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"corp_code", "bsns_year", "reprt_code"}
    )

    def __init__(
        self,
        *,
        dataset: DartCorporateDataset,
        corp_code: str,
        business_year: int | None = None,
        report_code: str | None = None,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if len(corp_code) != 8 or not corp_code.isdigit():
            raise ValueError("corp_code must be an 8-digit OpenDART corporation code")
        if dataset in _REPORT_DATASETS:
            if business_year is None or report_code is None:
                raise ValueError("report datasets require business_year and report_code")
            if report_code not in _REPORT_CODES:
                raise ValueError("unsupported OpenDART report code")
        elif business_year is not None or report_code is not None:
            raise ValueError("ownership dataset does not accept business_year/report_code")
        self.dataset = dataset
        self.corp_code = corp_code
        self.business_year = business_year
        self.report_code = report_code
        self._api_key = api_key
        self._transport = transport

    @property
    def path(self) -> str:
        return _ENDPOINTS[self.dataset]

    @property
    def base_url(self) -> str:
        return f"https://{self.HOST}{self.path}"

    def _credential(self) -> str:
        value = self._api_key or os.getenv("DART_API_KEY")
        if not value:
            raise MissingDartApiKey("DART_API_KEY is required for live fetch")
        return value

    def discover(self) -> list[str]:
        params = {"corp_code": self.corp_code}
        if self.dataset in _REPORT_DATASETS:
            assert self.business_year is not None and self.report_code is not None
            params["bsns_year"] = str(self.business_year)
            params["reprt_code"] = self.report_code
        return [f"{self.base_url}?{urlencode(params)}"]

    def _validated_query(self, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != self.HOST or parsed.path != self.path:
            raise ValueError("unsupported OpenDART corporate URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if {key.casefold() for key in raw} & {"crtfc_key", "key", "authkey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - self.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported OpenDART query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("corp_code") != self.corp_code:
            raise ValueError("OpenDART corp_code mismatch")
        if self.dataset in _REPORT_DATASETS:
            if query.get("bsns_year") != str(self.business_year):
                raise ValueError("OpenDART business year mismatch")
            if query.get("reprt_code") != self.report_code:
                raise ValueError("OpenDART report code mismatch")
        return query

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        params = query | {"crtfc_key": self._credential()}
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise DartApiError("OpenDART corporate API request failed") from None
        if not isinstance(payload, dict):
            raise DartApiError("OpenDART corporate API returned malformed JSON")
        status = str(payload.get("status") or "")
        if status != "000":
            raise DartApiError(f"OpenDART corporate API returned status {status or 'UNKNOWN'}")
        safe_payload = _redact_credentials(payload)
        return ConnectorDocument(
            url=url,
            title=f"OpenDART {self.dataset.value}",
            publisher="금융감독원 전자공시시스템 OpenDART",
            published_at=None,
            body=json.dumps(safe_payload, ensure_ascii=False, sort_keys=True),
            metadata={
                "dataset": self.dataset.value,
                "corp_code": self.corp_code,
                "business_year": "" if self.business_year is None else str(self.business_year),
                "report_code": self.report_code or "",
            },
        )

    def parse(
        self, document: ConnectorDocument
    ) -> list[DartExecutiveRecord | DartCompensationRecord | DartOwnershipRecord]:
        if self.dataset == DartCorporateDataset.EXECUTIVE_STATUS:
            return list(parse_executive_status(document))
        if self.dataset in {
            DartCorporateDataset.DIRECTOR_COMPENSATION_V2,
            DartCorporateDataset.TOP_COMPENSATION_V2,
        }:
            return list(parse_compensation(document, self.dataset))
        return list(parse_ownership(document))


def _redact_credentials(value):
    if isinstance(value, dict):
        return {
            key: _redact_credentials(item)
            for key, item in value.items()
            if key.casefold() not in {"crtfc_key", "key", "authkey"}
        }
    if isinstance(value, list):
        return [_redact_credentials(item) for item in value]
    return value


def _payload(document: ConnectorDocument) -> dict:
    try:
        payload = json.loads(document.body)
    except json.JSONDecodeError:
        raise DartApiError("OpenDART staged document is not valid JSON") from None
    if not isinstance(payload, dict) or str(payload.get("status") or "") != "000":
        raise DartApiError("OpenDART staged document is malformed")
    return payload


def _rows(payload: dict, key: str) -> list[dict]:
    rows = payload.get(key)
    if rows is None:
        return []
    if not isinstance(rows, list):
        raise DartApiError(f"OpenDART {key} rows are malformed")
    return [row for row in rows if isinstance(row, dict)]


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise DartApiError(f"OpenDART row missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return None if text in _EMPTY_MARKERS else text


def _date(value: str, key: str) -> date:
    normalized = value.replace(".", "-").replace("/", "-")
    if len(normalized) == 8 and normalized.isdigit():
        normalized = f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:8]}"
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise DartApiError(f"OpenDART row has invalid date: {key}") from None


def _optional_date(row: dict, key: str) -> date | None:
    value = _optional(row, key)
    return None if value is None else _date(value, key)


def _int_value(value: object) -> int | None:
    if value in (None, "", "-"):
        return None
    try:
        return int(str(value).replace(",", ""))
    except ValueError:
        return None


def _float_value(value: object) -> float | None:
    if value in (None, "", "-"):
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def parse_executive_status(document: ConnectorDocument) -> list[DartExecutiveRecord]:
    payload = _payload(document)
    records: list[DartExecutiveRecord] = []
    for row in _rows(payload, "list"):
        records.append(
            DartExecutiveRecord(
                receipt_no=_required(row, "rcept_no"),
                corp_code=_required(row, "corp_code"),
                corp_name=_required(row, "corp_name"),
                name=_required(row, "nm"),
                birth_year_month=_optional(row, "birth_ym"),
                position=_optional(row, "ofcps"),
                registered_status=_optional(row, "rgist_exctv_at"),
                full_time_status=_optional(row, "fte_at"),
                responsibility=_optional(row, "chrg_job"),
                reported_main_career=_optional(row, "main_career"),
                largest_shareholder_relation=_optional(row, "mxmm_shrholdr_relate"),
                tenure_text=_optional(row, "hffc_pd"),
                tenure_end_on=_optional_date(row, "tenure_end_on"),
                settlement_date=_date(_required(row, "stlm_dt"), "stlm_dt"),
            )
        )
    return records


def parse_compensation(
    document: ConnectorDocument, dataset: DartCorporateDataset
) -> list[DartCompensationRecord]:
    payload = _payload(document)
    receipt_no = _required(payload, "rcept_no")
    corp_code = _required(payload, "corp_code")
    corp_name = _required(payload, "corp_name")
    settlement_date = _date(_required(payload, "stlm_dt"), "stlm_dt")
    records: list[DartCompensationRecord] = []
    for row in _rows(payload, "group"):
        total = _int_value(row.get("mendng_totamt"))
        if total is None or total < 0:
            raise DartApiError("OpenDART compensation row has invalid total")
        records.append(
            DartCompensationRecord(
                receipt_no=receipt_no,
                corp_code=corp_code,
                corp_name=corp_name,
                name=_required(row, "nm"),
                position=_optional(row, "ofcps"),
                fiscal_year_label=_optional(row, "fscl_year"),
                compensation_total_krw=total,
                settlement_date=settlement_date,
                dataset=dataset,
            )
        )
    return records


def parse_ownership(document: ConnectorDocument) -> list[DartOwnershipRecord]:
    payload = _payload(document)
    records: list[DartOwnershipRecord] = []
    for row in _rows(payload, "list"):
        records.append(
            DartOwnershipRecord(
                receipt_no=_required(row, "rcept_no"),
                receipt_date=_date(_required(row, "rcept_dt"), "rcept_dt"),
                corp_code=_required(row, "corp_code"),
                corp_name=_required(row, "corp_name"),
                reporter_name=_required(row, "repror"),
                executive_registered_status=_optional(row, "isu_exctv_rgist_at"),
                executive_position=_optional(row, "isu_exctv_ofcps"),
                major_shareholder_relation=_optional(row, "isu_main_shrholdr"),
                security_count=_int_value(row.get("sp_stock_lmp_cnt")),
                security_change_count=_int_value(row.get("sp_stock_lmp_irds_cnt")),
                security_rate=_float_value(row.get("sp_stock_lmp_rate")),
                security_change_rate=_float_value(row.get("sp_stock_lmp_irds_rate")),
            )
        )
    return records
