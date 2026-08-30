from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class NkisApiError(RuntimeError):
    pass


class MissingNkisApiKey(NkisApiError):
    pass


POLICY_ID = UUID("14000000-0000-0000-0000-000000000001")


def nkis_research_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="nkis.re.kr",
        source_class="official_open_api",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license="NKIS API key requires application/review; no blanket commercial/fulltext right assumed",
        rate_limit="Provider-controlled; API key issued after application/review",
        policy_note=(
            "Reviewed 2026-08-30 against NKIS Open API introduction and ReportList/ReportDetail "
            "contracts. V0 stores research-output metadata only. Abstract/fulltext, AI use and "
            "commercial reuse remain disabled unless separately reviewed."
        ),
    )


@dataclass(frozen=True)
class NkisResearchOutput:
    output_id: str
    sequence: str
    title: str
    responsible_researcher_text: str | None
    publisher: str
    publication_year: int
    large_category_code: str | None = None
    large_category_name: str | None = None
    middle_category_code: str | None = None
    middle_category_name: str | None = None
    original_url: str | None = None


class NkisResearchReportConnector(Connector):
    HOST = "nkis.re.kr"
    PATH = "/nkisApi/search/ReportList.do"
    BASE_URL = f"https://{HOST}{PATH}"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {
            "pageNo",
            "rowCnt",
            "otpHanNm",
            "pubagc",
            "pubagcCd",
            "pblYyBegin",
            "pblYyEnd",
            "lclaScsId",
            "lclaScsNm",
        }
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        page_no: int = 1,
        row_count: int = 30,
        title: str | None = None,
        publisher: str | None = None,
        publisher_code: str | None = None,
        year_begin: int | None = None,
        year_end: int | None = None,
        large_category_code: str | None = None,
        large_category_name: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_no < 1:
            raise ValueError("page_no must be >= 1")
        if not 1 <= row_count <= 100:
            raise ValueError("row_count must be between 1 and 100")
        if year_begin and year_end and year_begin > year_end:
            raise ValueError("year_begin cannot be after year_end")
        self._api_key = api_key
        self.page_no = page_no
        self.row_count = row_count
        self.title = title
        self.publisher = publisher
        self.publisher_code = publisher_code
        self.year_begin = year_begin
        self.year_end = year_end
        self.large_category_code = large_category_code
        self.large_category_name = large_category_name
        self._transport = transport

    def _credential(self) -> str:
        value = self._api_key or os.getenv("NKIS_API_KEY")
        if not value:
            raise MissingNkisApiKey("NKIS_API_KEY is required for live fetch")
        return value

    def discover(self) -> list[str]:
        params: dict[str, str] = {
            "pageNo": str(self.page_no),
            "rowCnt": str(self.row_count),
        }
        for key, value in (
            ("otpHanNm", self.title),
            ("pubagc", self.publisher),
            ("pubagcCd", self.publisher_code),
            ("pblYyBegin", str(self.year_begin) if self.year_begin else None),
            ("pblYyEnd", str(self.year_end) if self.year_end else None),
            ("lclaScsId", self.large_category_code),
            ("lclaScsNm", self.large_category_name),
        ):
            if value:
                params[key] = value
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported NKIS API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if {key.casefold() for key in raw} & {"servicekey", "key", "authkey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported NKIS query parameter")
        return {key: values[-1] for key, values in raw.items()}

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = query | {"serviceKey": self._credential()}
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.BASE_URL, params=request_params)
                response.raise_for_status()
                body = response.text
        except httpx.HTTPError:
            raise NkisApiError("NKIS research API request failed") from None

        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            raise NkisApiError("NKIS research API returned malformed XML") from None
        if root.find(".//serviceKey") is not None:
            for element in root.findall(".//serviceKey"):
                element.text = None
            body = ET.tostring(root, encoding="unicode")

        total_count = _first_text(root, "TOTAL_COUNT")
        metadata = {
            "api": "ReportList",
            "page_no": query.get("pageNo", "1"),
            "row_count": query.get("rowCnt", "10"),
            "total_count": total_count or "",
        }
        for key in self.ALLOWED_QUERY - {"pageNo", "rowCnt"}:
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title="NKIS 연구보고서 목록",
            publisher="경제·인문사회연구회 국가정책연구포털",
            published_at=None,
            body=body,
            metadata=metadata,
        )

    @staticmethod
    def parse_outputs(document: ConnectorDocument) -> list[NkisResearchOutput]:
        try:
            root = ET.fromstring(document.body)
        except ET.ParseError:
            raise NkisApiError("NKIS research document is malformed XML") from None
        results = root.findall(".//result")
        if not results and root.tag == "result":
            results = [root]
        outputs: list[NkisResearchOutput] = []
        for result in results:
            output_id = _element_text(result, "OTP_ID")
            sequence = _element_text(result, "OTP_SEQ")
            title = _element_text(result, "OTP_HAN_NM")
            publisher = _element_text(result, "PUBAGC")
            year_text = _element_text(result, "PBL_YY")
            if not all((output_id, sequence, title, publisher, year_text)):
                raise NkisApiError("NKIS research row lacks required output fields")
            try:
                year = int(year_text)
            except ValueError:
                raise NkisApiError("NKIS research row has invalid publication year") from None
            outputs.append(
                NkisResearchOutput(
                    output_id=output_id,
                    sequence=sequence,
                    title=title,
                    responsible_researcher_text=_element_text(result, "INCHARGE_NM") or None,
                    publisher=publisher,
                    publication_year=year,
                    large_category_code=_element_text(result, "LCLA_SCS_ID") or None,
                    large_category_name=_element_text(result, "LCLA_SCS_NM") or None,
                    middle_category_code=_element_text(result, "MCLA_SCS_ID") or None,
                    middle_category_name=_element_text(result, "MCLA_SCS_NM") or None,
                    original_url=_element_text(result, "ORG_LINK") or None,
                )
            )
        return outputs


def _element_text(element: ET.Element, tag: str) -> str:
    child = element.find(tag)
    return "" if child is None or child.text is None else child.text.strip()


def _first_text(root: ET.Element, tag: str) -> str | None:
    child = root.find(f".//{tag}")
    if child is None or child.text is None:
        return None
    return child.text.strip() or None


_SIMPLE_PERSON_NAME = re.compile(r"^[가-힣]{2,5}$|^[A-Za-z][A-Za-z .'-]{1,79}$")


def responsible_researcher_candidate_name(value: str | None) -> str | None:
    """Return a safe single-person name or None when NKIS text is ambiguous/generic."""

    if value is None:
        return None
    text = " ".join(value.split())
    if not text or any(marker in text for marker in (",", ";", "/", " 외", "외 ", " 등")):
        return None
    if text in {"연구원", "연구진", "공동연구진", "편집진", "저자"}:
        return None
    return text if _SIMPLE_PERSON_NAME.fullmatch(text) else None
