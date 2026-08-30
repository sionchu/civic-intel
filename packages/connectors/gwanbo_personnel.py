from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class GwanboPersonnelError(RuntimeError):
    pass


@dataclass(frozen=True)
class GwanboPersonnelNotice:
    notice_id: str
    title: str
    publication_date: date
    gazette_name: str | None = None
    compilation_type: str | None = None
    publication_institution: str | None = None
    basis_law: str | None = None
    revision_reason: str | None = None
    detail_path: str | None = None


@dataclass(frozen=True)
class GwanboPersonnelPage:
    notices: tuple[GwanboPersonnelNotice, ...]
    total_count: int


POLICY_ID = UUID("11000000-0000-0000-0000-000000000002")


def gwanbo_personnel_policy() -> SourcePolicy:
    """Conservative policy for the official electronic-gazette personnel list.

    The Ministry site publicly labels this surface as an Open API, but the page does not
    state a reusable-data license. V0 therefore stores only the minimum list metadata and
    blocks raw/fulltext retention, excerpts, AI transmission and commercialization.
    """

    reviewed_at = datetime(2026, 8, 31, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="open.gwanbo.go.kr",
        source_class="official_open_api_html",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license=None,
        rate_limit="No published limit; sequential bounded date-window fetches only",
        policy_note=(
            "Reviewed against the Ministry of the Interior and Safety electronic-gazette "
            "personnel Open API page on 2026-08-31. The page exposes a public POST list "
            "interface but states no reuse license; raw HTML and linked originals are not "
            "retained. /robots.txt returned the site's not-found page."
        ),
    )


class _PersonnelTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.detail_calls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.casefold() == "onclick" and value and "fnDetail(" in value:
                self.detail_calls.append(value)

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)


_COUNT_RE = re.compile(r"총\s*건수\s*:\s*([0-9,]+)\s*건")
_DETAIL_CALL_RE = re.compile(r"fnDetail\s*\((.*)\)\s*;?", re.DOTALL)


def _parse_javascript_arguments(call: str) -> list[str]:
    match = _DETAIL_CALL_RE.search(call)
    if match is None:
        raise GwanboPersonnelError("Gwanbo personnel detail call is malformed")
    payload = match.group(1)
    values: list[str] = []
    index = 0
    while index < len(payload):
        while index < len(payload) and payload[index].isspace():
            index += 1
        if index >= len(payload) or payload[index] not in {"'", '"'}:
            raise GwanboPersonnelError("Gwanbo personnel detail arguments are malformed")
        quote = payload[index]
        index += 1
        buffer: list[str] = []
        while index < len(payload):
            character = payload[index]
            if character == "\\":
                index += 1
                if index >= len(payload):
                    raise GwanboPersonnelError("Gwanbo personnel detail escape is malformed")
                buffer.append(payload[index])
                index += 1
                continue
            if character == quote:
                index += 1
                break
            buffer.append(character)
            index += 1
        else:
            raise GwanboPersonnelError("Gwanbo personnel detail string is unterminated")
        values.append(html.unescape("".join(buffer)).strip())
        while index < len(payload) and payload[index].isspace():
            index += 1
        if index == len(payload):
            break
        if payload[index] != ",":
            raise GwanboPersonnelError("Gwanbo personnel detail arguments are malformed")
        index += 1
    return values


class GwanboPersonnelConnector(Connector):
    LIST_URL = "https://open.gwanbo.go.kr/OpenApi/web/personnelList"
    AJAX_URL = "https://open.gwanbo.go.kr/OpenApi/web/personnelListAjax"
    HOST = "open.gwanbo.go.kr"
    LIST_PATH = "/OpenApi/web/personnelList"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"reqFrom", "reqTo", "currentPage", "rowPerPage"}
    )

    def __init__(
        self,
        *,
        date_from: date,
        date_to: date,
        page_index: int = 1,
        page_size: int = 10,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if date_from > date_to:
            raise ValueError("date_from must not be after date_to")
        if (date_to - date_from).days > 1098:
            raise ValueError("Gwanbo enumeration window must not exceed three years")
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 100:
            raise ValueError("page_size must be between 1 and 100")
        self.date_from = date_from
        self.date_to = date_to
        self.page_index = page_index
        self.page_size = page_size
        self._transport = transport

    def discover(self) -> list[str]:
        params = {
            "reqFrom": self.date_from.strftime("%Y.%m.%d"),
            "reqTo": self.date_to.strftime("%Y.%m.%d"),
            "currentPage": str(self.page_index),
            "rowPerPage": str(self.page_size),
        }
        return [f"{self.LIST_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.LIST_PATH:
            raise ValueError("unsupported Gwanbo personnel URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported Gwanbo personnel query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        required = cls.ALLOWED_QUERY
        if not required.issubset(query):
            raise ValueError("Gwanbo personnel URL lacks a required bounded-scope parameter")
        return query

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_data = {
            "rowPerPage": query["rowPerPage"],
            "currentPage": query["currentPage"],
            "themaSe": "06",
            "reqFrom": query["reqFrom"],
            "reqTo": query["reqTo"],
            "search": "",
            "pblcnSearch": "",
            "lawNmSearch": "",
        }
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.post(self.AJAX_URL, data=request_data)
                response.raise_for_status()
                body = response.text
        except httpx.HTTPError:
            raise GwanboPersonnelError("Gwanbo personnel API request failed") from None

        page = self.parse_page_body(body)
        metadata = {
            "source_contract": "gwanbo_personnel_notice_list",
            "date_from": query["reqFrom"],
            "date_to": query["reqTo"],
            "page_index": query["currentPage"],
            "page_size": query["rowPerPage"],
            "row_count": str(len(page.notices)),
            "list_total_count": str(page.total_count),
        }
        return ConnectorDocument(
            url=url,
            title="대한민국 전자관보 인사 API",
            publisher="행정안전부",
            published_at=None,
            body=body,
            metadata=metadata,
        )

    @classmethod
    def parse_page_body(cls, body: str) -> GwanboPersonnelPage:
        parser = _PersonnelTableParser()
        parser.feed(body)
        text = " ".join(part.strip() for part in parser.text_parts if part.strip())
        count_match = _COUNT_RE.search(text)
        if count_match is None:
            if not parser.detail_calls and "검색결과가 존재하지 않습니다" in text:
                total_count = 0
            else:
                raise GwanboPersonnelError("Gwanbo personnel total count is unavailable")
        else:
            total_count = int(count_match.group(1).replace(",", ""))

        notices: list[GwanboPersonnelNotice] = []
        for call in parser.detail_calls:
            values = _parse_javascript_arguments(call)
            if len(values) != 11:
                raise GwanboPersonnelError("Gwanbo personnel detail field count changed")
            notice_id, title, published, gazette, compilation, institution, basis_law = values[:7]
            revision_reason, detail_path = values[9], values[10]
            if not notice_id or not title or not published:
                raise GwanboPersonnelError("Gwanbo personnel row lacks required notice anchors")
            try:
                publication_date = date.fromisoformat(published.replace(".", "-"))
            except ValueError:
                raise GwanboPersonnelError(
                    "Gwanbo personnel publication date is malformed"
                ) from None
            optional = lambda value: value or None
            notices.append(
                GwanboPersonnelNotice(
                    notice_id=notice_id,
                    title=title,
                    publication_date=publication_date,
                    gazette_name=optional(gazette),
                    compilation_type=optional(compilation),
                    publication_institution=optional(institution),
                    basis_law=optional(basis_law),
                    revision_reason=optional(revision_reason),
                    detail_path=optional(detail_path),
                )
            )
        if len(notices) > total_count:
            raise GwanboPersonnelError("Gwanbo personnel page exceeds provider total count")
        return GwanboPersonnelPage(tuple(notices), total_count)

    @classmethod
    def parse_notices(cls, document: ConnectorDocument) -> list[GwanboPersonnelNotice]:
        return list(cls.parse_page_body(document.body).notices)
