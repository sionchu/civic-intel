from __future__ import annotations

import html
import json
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from math import ceil
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urljoin, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import (
    PublicInstitutionClassification,
    PublicInstitutionExecutiveKind,
    SourceCollectionMode,
)

from .base import Connector, ConnectorDocument


class AlioRecordError(ValueError):
    pass


POLICY_ID = UUID("13000000-0000-0000-0000-000000000001")


def alio_public_institution_policy() -> SourcePolicy:
    """Reviewed metadata policy for ALIO public-institution disclosures."""

    reviewed_at = datetime(2026, 8, 31, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="alio.go.kr",
        source_class="official_structured_disclosure",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        terms_checked_at=reviewed_at,
        license=(
            "ALIO 저작권 정책: ALIO가 저작재산권을 전부 보유한 저작물은 별도 허락 "
            "없이 자유이용; 공공데이터는 영리 목적을 포함해 자유 활용"
        ),
        rate_limit="No published limit; sequential bounded item-4 institution enumeration only",
        policy_note=(
            "Reviewed 2026-08-31 against the official ALIO item catalog, item 4 institution "
            "directory/report/document surfaces, copyright policy and robots.txt. Fetch and "
            "normalized metadata storage are permitted. Full report HTML, disclosure-staff "
            "contacts, excerpts and AI transmission remain excluded by data minimization."
        ),
    )


_CLASSIFICATION_MAP = {
    "공기업": PublicInstitutionClassification.PUBLIC_CORPORATION,
    "준정부기관": PublicInstitutionClassification.QUASI_GOVERNMENT,
    "기타공공기관": PublicInstitutionClassification.OTHER_PUBLIC_INSTITUTION,
}

_EXECUTIVE_KIND_MAP = {
    "상임기관장": PublicInstitutionExecutiveKind.INSTITUTION_HEAD,
    "기관장": PublicInstitutionExecutiveKind.INSTITUTION_HEAD,
    "상임감사": PublicInstitutionExecutiveKind.STANDING_AUDITOR,
    "상임감사위원": PublicInstitutionExecutiveKind.STANDING_AUDITOR,
    "상임이사": PublicInstitutionExecutiveKind.STANDING_DIRECTOR,
    "비상임이사": PublicInstitutionExecutiveKind.NON_STANDING_DIRECTOR,
    "비상임이사(감사위원)": PublicInstitutionExecutiveKind.NON_STANDING_DIRECTOR,
    "비상임감사": PublicInstitutionExecutiveKind.NON_STANDING_AUDITOR,
}

_EXECUTIVE_REEMPLOYMENT_LABELS = frozenset({"임원", "기관장", "상임임원", "비상임임원"})
_MASK_CHARS = frozenset({"○", "●", "*", "＊", "□", "■"})


@dataclass(frozen=True)
class AlioInstitutionRecord:
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    classification_text: str
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioExecutiveRecord:
    record_id: str
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    classification_text: str
    person_name: str
    position_text: str
    title: str
    executive_kind: PublicInstitutionExecutiveKind
    term_start: date
    term_end: date | None
    reported_careers: tuple[str, ...]
    selection_procedure: str | None
    selection_rule: str | None
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioCompensationRecord:
    record_id: str
    institution_code: str
    institution_name: str
    classification: PublicInstitutionClassification
    executive_kind: PublicInstitutionExecutiveKind
    fiscal_year: int
    basis: str
    total_thousand_krw: int
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioReemploymentRecord:
    record_id: str
    institution_code: str
    institution_name: str
    person_name: str | None
    former_kind: str
    former_title: str | None
    retirement_date: date
    destination_organization: str
    reemployment_date: date
    relationship: str | None
    executive_person_scope: bool
    as_of: date
    source_ref: str


@dataclass(frozen=True)
class AlioInstitutionSummary:
    institution_code: str
    institution_name: str
    institution_type_code: str
    classification: PublicInstitutionClassification
    classification_text: str


@dataclass(frozen=True)
class AlioInstitutionDirectory:
    institutions: tuple[AlioInstitutionSummary, ...]
    total_count: int


@dataclass(frozen=True)
class AlioExecutiveDisclosure:
    rank: int
    disclosure_no: str
    institution_code: str
    report_form_no: str
    disclosure_date: date


@dataclass(frozen=True)
class AlioExecutiveDisclosurePage:
    disclosures: tuple[AlioExecutiveDisclosure, ...]
    page_no: int
    page_size: int
    total_count: int
    total_pages: int


def _required(row: dict, key: str) -> str:
    value = row.get(key)
    text = "" if value is None else str(value).strip()
    if not text:
        raise AlioRecordError(f"missing required field: {key}")
    return text


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _date_value(row: dict, key: str, *, required: bool = True) -> date | None:
    value = _optional(row, key)
    if value is None:
        if required:
            raise AlioRecordError(f"missing required field: {key}")
        return None
    normalized = value.replace("년", "-").replace("월", "-").replace("일", "")
    normalized = "-".join(
        part.strip() for part in normalized.replace(".", "-").split("-") if part.strip()
    )
    try:
        if len(normalized) == 8 and normalized.isdigit():
            return date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:8]))
        parts = normalized.split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except ValueError:
        pass
    raise AlioRecordError(f"invalid date: {key}")


def _classification(row: dict) -> tuple[PublicInstitutionClassification, str]:
    text = _required(row, "기관분류")
    return _classification_text(text)


def _classification_text(text: str) -> tuple[PublicInstitutionClassification, str]:
    normalized = text
    if "공기업" in text:
        normalized = "공기업"
    elif "준정부기관" in text:
        normalized = "준정부기관"
    elif "기타공공기관" in text:
        normalized = "기타공공기관"
    try:
        return _CLASSIFICATION_MAP[normalized], text
    except KeyError:
        raise AlioRecordError(f"unsupported public-institution classification: {text}") from None


def _executive_kind(value: str) -> PublicInstitutionExecutiveKind:
    normalized = value.strip()
    if normalized.startswith("상임기관장"):
        normalized = "상임기관장"
    elif normalized.startswith("상임감사위원"):
        normalized = "상임감사위원"
    elif normalized.startswith("상임감사"):
        normalized = "상임감사"
    elif normalized.startswith("상임이사"):
        normalized = "상임이사"
    elif normalized.startswith("비상임이사(감사위원)"):
        normalized = "비상임이사(감사위원)"
    elif normalized.startswith("비상임이사"):
        normalized = "비상임이사"
    elif normalized.startswith("비상임감사"):
        normalized = "비상임감사"
    try:
        return _EXECUTIVE_KIND_MAP[normalized]
    except KeyError:
        raise AlioRecordError(f"unsupported ALIO executive position: {value}") from None


def _public_name(value: str | None) -> str | None:
    if value is None:
        return None
    compact = "".join(value.split())
    if (
        not compact
        or compact in {"-", "공석", "해당없음"}
        or any(char in _MASK_CHARS for char in compact)
    ):
        return None
    return value.strip()


def _reported_careers(row: dict) -> tuple[str, ...]:
    raw = row.get("주요경력")
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(text for item in raw if (text := str(item).strip()))
    text = str(raw).strip()
    if not text:
        return ()
    return tuple(part.strip() for part in text.split("\n") if part.strip())


def parse_institution_rows(rows: list[dict]) -> list[AlioInstitutionRecord]:
    records: list[AlioInstitutionRecord] = []
    for row in rows:
        classification, classification_text = _classification(row)
        as_of = _date_value(row, "기준일")
        assert as_of is not None
        records.append(
            AlioInstitutionRecord(
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                classification_text=classification_text,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_executive_rows(rows: list[dict]) -> list[AlioExecutiveRecord]:
    records: list[AlioExecutiveRecord] = []
    for row in rows:
        classification, classification_text = _classification(row)
        position = _required(row, "직위")
        person_name = _public_name(_required(row, "성명"))
        if person_name is None:
            raise AlioRecordError("masked executive name cannot create an executive candidate")
        term_start = _date_value(row, "임기_시작일")
        term_end = _date_value(row, "임기_종료일", required=False)
        as_of = _date_value(row, "기준일")
        assert term_start is not None and as_of is not None
        records.append(
            AlioExecutiveRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                classification_text=classification_text,
                person_name=person_name,
                position_text=position,
                title=_required(row, "직책"),
                executive_kind=_executive_kind(position),
                term_start=term_start,
                term_end=term_end,
                reported_careers=_reported_careers(row),
                selection_procedure=_optional(row, "선임절차"),
                selection_rule=_optional(row, "선임절차규정"),
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_compensation_rows(rows: list[dict]) -> list[AlioCompensationRecord]:
    records: list[AlioCompensationRecord] = []
    for row in rows:
        classification, _ = _classification(row)
        year_text = _required(row, "연도")
        amount_text = _required(row, "합계_천원").replace(",", "")
        try:
            fiscal_year = int(year_text)
            total = int(amount_text)
        except ValueError:
            raise AlioRecordError("invalid ALIO compensation number") from None
        if fiscal_year < 1900 or total < 0:
            raise AlioRecordError("invalid ALIO compensation value")
        as_of = _date_value(row, "기준일")
        assert as_of is not None
        records.append(
            AlioCompensationRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                classification=classification,
                executive_kind=_executive_kind(_required(row, "직위구분")),
                fiscal_year=fiscal_year,
                basis=_required(row, "기준"),
                total_thousand_krw=total,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


def parse_reemployment_rows(rows: list[dict]) -> list[AlioReemploymentRecord]:
    records: list[AlioReemploymentRecord] = []
    for row in rows:
        former_kind = _required(row, "구분")
        executive_scope = former_kind in _EXECUTIVE_REEMPLOYMENT_LABELS
        retirement_date = _date_value(row, "퇴직일")
        reemployment_date = _date_value(row, "재취업일")
        as_of = _date_value(row, "기준일")
        assert retirement_date is not None and reemployment_date is not None and as_of is not None
        person_name = _public_name(_optional(row, "퇴직_임직원명")) if executive_scope else None
        records.append(
            AlioReemploymentRecord(
                record_id=_required(row, "record_id"),
                institution_code=_required(row, "기관코드"),
                institution_name=_required(row, "기관명"),
                person_name=person_name,
                former_kind=former_kind,
                former_title=_optional(row, "직위_급"),
                retirement_date=retirement_date,
                destination_organization=_required(row, "재취업회사명"),
                reemployment_date=reemployment_date,
                relationship=_optional(row, "관계"),
                executive_person_scope=executive_scope and person_name is not None,
                as_of=as_of,
                source_ref=_required(row, "source_ref"),
            )
        )
    return records


class _AlioReportTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._table = []
        elif normalized == "tr" and self._table_depth == 1:
            self._row = []
        elif normalized in {"td", "th"} and self._table_depth == 1 and self._row is not None:
            self._cell_parts = []
        elif normalized == "br" and self._cell_parts is not None:
            self._cell_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in {"td", "th"} and self._cell_parts is not None:
            assert self._row is not None
            lines = [
                re.sub(r"\s+", " ", html.unescape(part)).strip()
                for part in "".join(self._cell_parts).split("\n")
            ]
            self._row.append("\n".join(part for part in lines if part))
            self._cell_parts = None
        elif normalized == "tr" and self._table_depth == 1 and self._row is not None:
            if any(self._row):
                assert self._table is not None
                self._table.append(self._row)
            self._row = None
        elif normalized == "table" and self._table_depth:
            if self._table_depth == 1 and self._table is not None:
                if self._table:
                    self.tables.append(self._table)
                self._table = None
            self._table_depth -= 1


def _row_value(row: list[str], label: str) -> str | None:
    try:
        index = row.index(label)
    except ValueError:
        return None
    if index + 1 >= len(row):
        return None
    return row[index + 1].strip() or None


def _report_date(value: str, field: str) -> date:
    normalized = value.replace("년", "-").replace("월", "-").replace("일", "").replace(".", "-")
    normalized = "-".join(part.strip() for part in normalized.split("-") if part.strip())
    try:
        return date.fromisoformat(normalized)
    except ValueError:
        raise AlioRecordError(f"invalid ALIO report date: {field}") from None


def _optional_report_date(value: str | None, field: str) -> date | None:
    if value is None or value.strip() in {"", "-", "재직기간", "현재", "해당없음"}:
        return None
    return _report_date(value, field)


class AlioExecutiveDisclosureConnector(Connector):
    HOST = "alio.go.kr"
    BASE_URL = f"https://{HOST}"
    REPORT_FORM_NO = "20305"
    DIRECTORY_PATH = "/item/itemOrganList.do"
    DIRECTORY_API_PATH = "/item/itemOrganListSusi.json"
    REPORT_LIST_API_PATH = "/item/itemReportListSusi.json"
    REPORT_PATH = "/item/itemReport.do"
    REPORT_PAGE_SIZE = 10
    ALLOWED_DIRECTORY_QUERY: ClassVar[frozenset[str]] = frozenset({"reportFormRootNo"})
    ALLOWED_REPORT_LIST_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"reportFormRootNo", "apbaId", "apbaType", "pageNo"}
    )
    ALLOWED_REPORT_QUERY: ClassVar[frozenset[str]] = frozenset({"seq", "disclosureNo"})
    _DOC_PATH_RE = re.compile(
        r"[\"'](?P<path>/upload/disclosure/[0-9]{4}/[0-9]{2}/[0-9]{2}/"
        r"(?P<disclosure>[0-9]+)/doc\.html)[\"']"
    )

    def __init__(self, *, transport: httpx.BaseTransport | None = None) -> None:
        self._transport = transport

    def discover(self) -> list[str]:
        return [
            (
                f"{self.BASE_URL}{self.DIRECTORY_PATH}?"
                f"{urlencode({'reportFormRootNo': self.REPORT_FORM_NO})}"
            )
        ]

    def report_list_url(self, institution: AlioInstitutionSummary, page_no: int = 1) -> str:
        if page_no < 1:
            raise ValueError("ALIO report page number must be positive")
        query = urlencode(
            {
                "reportFormRootNo": self.REPORT_FORM_NO,
                "apbaId": institution.institution_code,
                "apbaType": institution.institution_type_code,
                "pageNo": str(page_no),
            }
        )
        return f"{self.BASE_URL}{self.REPORT_LIST_API_PATH}?{query}"

    def report_url(self, disclosure: AlioExecutiveDisclosure) -> str:
        query = urlencode(
            {
                "seq": disclosure.disclosure_no,
                "disclosureNo": disclosure.disclosure_no,
            }
        )
        return f"{self.BASE_URL}{self.REPORT_PATH}?{query}"

    @classmethod
    def _validated_query(
        cls,
        url: str,
        *,
        path: str,
        allowed: frozenset[str],
    ) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != path:
            raise ValueError("unsupported ALIO disclosure URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if set(raw) != set(allowed) or any(len(values) != 1 for values in raw.values()):
            raise ValueError("ALIO disclosure URL has an invalid bounded query")
        query = {key: values[0] for key, values in raw.items()}
        if query.get("reportFormRootNo", cls.REPORT_FORM_NO) != cls.REPORT_FORM_NO:
            raise ValueError("ALIO disclosure URL must use item 4")
        return query

    def _client(self) -> httpx.Client:
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        return httpx.Client(transport=self._transport, timeout=20, headers=headers)

    def fetch(self, url: str) -> ConnectorDocument:
        parsed = urlparse(url)
        try:
            with self._client() as client:
                if parsed.path == self.DIRECTORY_PATH:
                    self._validated_query(
                        url,
                        path=self.DIRECTORY_PATH,
                        allowed=self.ALLOWED_DIRECTORY_QUERY,
                    )
                    response = client.post(
                        f"{self.BASE_URL}{self.DIRECTORY_API_PATH}",
                        json={
                            "apbaType": [],
                            "apbaId": "",
                            "reportFormRootNo": self.REPORT_FORM_NO,
                        },
                    )
                    response.raise_for_status()
                    body = response.text
                    directory = self.parse_directory_body(body)
                    return ConnectorDocument(
                        url=url,
                        title="ALIO 항목 4 임원현황 기관 목록",
                        publisher="재정경제부",
                        published_at=None,
                        body=body,
                        metadata={
                            "source_contract": "alio_item_4_institution_directory",
                            "report_form_no": self.REPORT_FORM_NO,
                            "institution_total": str(directory.total_count),
                        },
                    )
                if parsed.path == self.REPORT_LIST_API_PATH:
                    query = self._validated_query(
                        url,
                        path=self.REPORT_LIST_API_PATH,
                        allowed=self.ALLOWED_REPORT_LIST_QUERY,
                    )
                    try:
                        page_no = int(query["pageNo"])
                    except ValueError:
                        raise ValueError("ALIO report page number is invalid") from None
                    if page_no < 1:
                        raise ValueError("ALIO report page number must be positive")
                    response = client.post(
                        f"{self.BASE_URL}{self.REPORT_LIST_API_PATH}",
                        json={
                            "pageNo": page_no,
                            "apbaId": query["apbaId"],
                            "apbaType": query["apbaType"],
                            "reportFormRootNo": self.REPORT_FORM_NO,
                            "search_word": "",
                            "search_flag": "",
                            "bid_type": "",
                            "enfc_istt": "",
                        },
                    )
                    response.raise_for_status()
                    body = response.text
                    page = self.parse_report_page_body(
                        body,
                        institution_code=query["apbaId"],
                        requested_page=page_no,
                    )
                    return ConnectorDocument(
                        url=url,
                        title="ALIO 항목 4 임원현황 공시 목록",
                        publisher="재정경제부",
                        published_at=None,
                        body=body,
                        metadata={
                            "source_contract": "alio_item_4_report_list",
                            "report_form_no": self.REPORT_FORM_NO,
                            "institution_code": query["apbaId"],
                            "page_no": str(page.page_no),
                            "page_size": str(page.page_size),
                            "list_total_count": str(page.total_count),
                            "total_pages": str(page.total_pages),
                        },
                    )
                if parsed.path == self.REPORT_PATH:
                    query = self._validated_query(
                        url,
                        path=self.REPORT_PATH,
                        allowed=self.ALLOWED_REPORT_QUERY,
                    )
                    if query["seq"] != query["disclosureNo"] or not query["seq"].isdigit():
                        raise ValueError("ALIO report disclosure identity is invalid")
                    response = client.get(url)
                    response.raise_for_status()
                    matches = {
                        match.group("path")
                        for match in self._DOC_PATH_RE.finditer(response.text)
                        if match.group("disclosure") == query["disclosureNo"]
                    }
                    if len(matches) != 1:
                        raise AlioRecordError("ALIO report document path is unavailable")
                    document_path = next(iter(matches))
                    document_response = client.get(urljoin(self.BASE_URL, document_path))
                    document_response.raise_for_status()
                    return ConnectorDocument(
                        url=url,
                        title="ALIO 항목 4 임원현황 공시",
                        publisher="재정경제부",
                        published_at=None,
                        body=document_response.text,
                        metadata={
                            "source_contract": "alio_item_4_executive_report",
                            "report_form_no": self.REPORT_FORM_NO,
                            "disclosure_no": query["disclosureNo"],
                            "document_path": document_path,
                        },
                    )
        except httpx.HTTPError:
            raise AlioRecordError("ALIO item 4 request failed") from None
        raise ValueError("unsupported ALIO disclosure URL")

    @classmethod
    def _json_data(cls, body: str) -> dict:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise AlioRecordError("ALIO response is not valid JSON") from None
        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise AlioRecordError("ALIO response did not report success")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise AlioRecordError("ALIO response data is unavailable")
        return data

    @classmethod
    def parse_directory_body(cls, body: str) -> AlioInstitutionDirectory:
        data = cls._json_data(body)
        rows = data.get("organList")
        total = data.get("totalCnt")
        if not isinstance(rows, list) or not isinstance(total, int) or total < 0:
            raise AlioRecordError("ALIO institution directory contract changed")
        institutions: list[AlioInstitutionSummary] = []
        seen: set[str] = set()
        for raw in rows:
            if not isinstance(raw, dict):
                raise AlioRecordError("ALIO institution row is invalid")
            code = _required(raw, "apbaId")
            if code in seen:
                raise AlioRecordError("duplicate ALIO institution identifier")
            seen.add(code)
            classification, classification_text = _classification_text(_required(raw, "typeNa"))
            institutions.append(
                AlioInstitutionSummary(
                    institution_code=code,
                    institution_name=_required(raw, "apbaNa"),
                    institution_type_code=_required(raw, "apbaType"),
                    classification=classification,
                    classification_text=classification_text,
                )
            )
        if total != len(institutions):
            raise AlioRecordError("ALIO institution directory coverage is incomplete")
        return AlioInstitutionDirectory(tuple(institutions), total)

    @classmethod
    def parse_report_page_body(
        cls,
        body: str,
        *,
        institution_code: str,
        requested_page: int,
    ) -> AlioExecutiveDisclosurePage:
        data = cls._json_data(body)
        rows = data.get("result")
        page = data.get("page")
        if not isinstance(rows, list) or not isinstance(page, dict):
            raise AlioRecordError("ALIO report-list contract changed")
        try:
            page_no = int(page["currPage"])
            page_size = int(page["unitPage"])
            total_count = int(page["totalCount"])
            total_pages = int(page["totalPage"])
        except (KeyError, TypeError, ValueError):
            raise AlioRecordError("ALIO report pagination is unavailable") from None
        if page_no != requested_page or page_size != cls.REPORT_PAGE_SIZE:
            raise AlioRecordError("ALIO report pagination is inconsistent")
        expected_pages = ceil(total_count / page_size) if total_count else 0
        if total_count < 0 or total_pages != expected_pages:
            raise AlioRecordError("ALIO report total-page coverage is inconsistent")
        expected_rows = min(page_size, max(total_count - ((page_no - 1) * page_size), 0))
        if len(rows) != expected_rows:
            raise AlioRecordError("ALIO report page row count is incomplete")

        disclosures: list[AlioExecutiveDisclosure] = []
        ranks: set[int] = set()
        disclosure_ids: set[str] = set()
        for raw in rows:
            if not isinstance(raw, dict):
                raise AlioRecordError("ALIO report-list row is invalid")
            try:
                rank = int(raw["rnum"])
            except (KeyError, TypeError, ValueError):
                raise AlioRecordError("ALIO report rank is invalid") from None
            disclosure_no = _required(raw, "disclosureNo")
            if rank in ranks or disclosure_no in disclosure_ids:
                raise AlioRecordError("duplicate ALIO report identity")
            if _required(raw, "apbaId") != institution_code:
                raise AlioRecordError("ALIO report institution identifier is inconsistent")
            if _required(raw, "reportFormNo") != cls.REPORT_FORM_NO:
                raise AlioRecordError("ALIO report form is not item 4")
            if _required(raw, "reportGbn") != "Y":
                raise AlioRecordError("ALIO item 4 row is not a report")
            if not disclosure_no.isdigit():
                raise AlioRecordError("ALIO disclosure identifier is invalid")
            ranks.add(rank)
            disclosure_ids.add(disclosure_no)
            disclosures.append(
                AlioExecutiveDisclosure(
                    rank=rank,
                    disclosure_no=disclosure_no,
                    institution_code=institution_code,
                    report_form_no=cls.REPORT_FORM_NO,
                    disclosure_date=_report_date(_required(raw, "idate"), "idate"),
                )
            )
        return AlioExecutiveDisclosurePage(
            tuple(disclosures), page_no, page_size, total_count, total_pages
        )

    @classmethod
    def current_disclosure(cls, page: AlioExecutiveDisclosurePage) -> AlioExecutiveDisclosure:
        current = [item for item in page.disclosures if item.rank == 1]
        if page.page_no != 1 or len(current) != 1:
            raise AlioRecordError("ALIO current item 4 disclosure is unavailable")
        return current[0]

    @classmethod
    def parse_executives(
        cls,
        document: ConnectorDocument,
        *,
        institution: AlioInstitutionSummary,
        disclosure: AlioExecutiveDisclosure,
    ) -> list[AlioExecutiveRecord]:
        if document.metadata.get("disclosure_no") != disclosure.disclosure_no:
            raise AlioRecordError("ALIO report document identity is inconsistent")
        parser = _AlioReportTableParser()
        parser.feed(document.body)
        as_of: date | None = None
        for table in parser.tables:
            for row in table:
                value = _row_value(row, "기준일")
                if value is not None:
                    parsed = _report_date(value, "기준일")
                    if as_of is not None and as_of != parsed:
                        raise AlioRecordError("ALIO report has conflicting as-of dates")
                    as_of = parsed
        if as_of is None:
            raise AlioRecordError("ALIO report as-of date is unavailable")

        records: list[AlioExecutiveRecord] = []
        for table in parser.tables:
            if not table or "직위" not in table[0] or "성명" not in table[0]:
                continue
            position = _row_value(table[0], "직위")
            person_value = _row_value(table[0], "성명")
            if position is None or person_value is None:
                raise AlioRecordError("ALIO executive table lacks position or name")
            person_name = _public_name(person_value)
            if person_name is None:
                raise AlioRecordError("masked or vacant ALIO executive cannot be enumerated")
            title: str | None = None
            term_start_value: str | None = None
            term_end_value: str | None = None
            careers: tuple[str, ...] = ()
            selection_procedure: str | None = None
            selection_rule: str | None = None
            for row in table[1:]:
                title = title or _row_value(row, "직책")
                term_start_value = term_start_value or _row_value(row, "(시작일)")
                term_end_value = term_end_value or _row_value(row, "(종료일)")
                career_value = _row_value(row, "주요경력")
                if career_value is not None:
                    careers = tuple(
                        part.strip() for part in career_value.split("\n") if part.strip()
                    )
                selection_procedure = selection_procedure or _row_value(row, "선임절차")
                selection_rule = selection_rule or _row_value(row, "선임절차규정")
            if title is None or term_start_value is None:
                raise AlioRecordError("ALIO executive table lacks title or term start")
            ordinal = len(records) + 1
            records.append(
                AlioExecutiveRecord(
                    record_id=f"{disclosure.disclosure_no}:{ordinal}",
                    institution_code=institution.institution_code,
                    institution_name=institution.institution_name,
                    classification=institution.classification,
                    classification_text=institution.classification_text,
                    person_name=person_name,
                    position_text=position,
                    title=title,
                    executive_kind=_executive_kind(position),
                    term_start=_report_date(term_start_value, "임기 시작일"),
                    term_end=_optional_report_date(term_end_value, "임기 종료일"),
                    reported_careers=careers,
                    selection_procedure=selection_procedure,
                    selection_rule=selection_rule,
                    as_of=as_of,
                    source_ref=disclosure.disclosure_no,
                )
            )
        if not records:
            raise AlioRecordError("ALIO report has no supported executive rows")
        return records
