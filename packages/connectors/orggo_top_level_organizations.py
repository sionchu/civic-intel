from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class OrgGoTopLevelOrganizationError(RuntimeError):
    pass


POLICY_ID = UUID("e02949cb-5e1e-5304-b2e3-495e3d258fe4")


def orggo_top_level_organization_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 9, 22, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="www.org.go.kr",
        source_class="official_government_organization_html",
        collection_mode=SourceCollectionMode.HTTP,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=False,
        terms_checked_at=reviewed_at,
        license=None,
        rate_limit="No published limit; sequential bounded top-level list pages only",
        policy_note=(
            "Reviewed against the MOIS Government Organization Management System on 2026-09-22. "
            "The public institution-chart list is fetchable and robots.txt blocks /search only, "
            "but the site displays All rights reserved and no blanket reuse license was found. "
            "V0 therefore keeps normalized list metadata only and blocks fulltext retention, "
            "excerpt display, AI transmission and commercialization."
        ),
    )


@dataclass(frozen=True)
class OrgGoTopLevelOrganizationRecord:
    organization_name: str
    category: str
    org_code: str
    chart_id: str


@dataclass(frozen=True)
class OrgGoTopLevelOrganizationPage:
    organizations: tuple[OrgGoTopLevelOrganizationRecord, ...]
    total_count: int


_DETAIL_RE = re.compile(
    r"^javascript:openDetail\('([^']+)'\s*,\s*'([0-9]{7})'\s*,\s*'([0-9]+)'\)$"
)
_COUNT_RE = re.compile(r"총\s*([0-9,]+)\s*건")


class _OrgGoListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.rows: list[tuple[str, str, str, str]] = []
        self._current: tuple[str, str, str, list[str]] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() != "a":
            return
        values = {key.casefold(): value for key, value in attrs}
        classes = set((values.get("class") or "").split())
        if "subject" not in classes:
            return
        href = values.get("href") or ""
        match = _DETAIL_RE.fullmatch(href.strip())
        if match is None:
            raise OrgGoTopLevelOrganizationError(
                "org.go subject row has malformed detail locator"
            )
        self._current = (match.group(1).strip(), match.group(2), match.group(3), [])

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self._current is not None:
            self._current[3].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() != "a" or self._current is None:
            return
        category, org_code, chart_id, parts = self._current
        name = " ".join(part.strip() for part in parts if part.strip()).strip()
        self.rows.append((name, category, org_code, chart_id))
        self._current = None


class OrgGoTopLevelOrganizationConnector(Connector):
    HOST = "www.org.go.kr"
    PATH = "/cop/bbs/getInstiChartList.do"
    BASE_URL = f"https://{HOST}{PATH}"
    TITLE = "정부조직관리정보시스템 기관별기구도"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset({"pageIndex"})

    def __init__(
        self,
        *,
        page_index: int = 1,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        self.page_index = page_index
        self._transport = transport

    def discover(self) -> list[str]:
        return [f"{self.BASE_URL}?{urlencode({'pageIndex': self.page_index})}"]

    @classmethod
    def _validated_query(cls, url: str) -> int:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported org.go institution-chart URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported org.go institution-chart query parameter")
        values = raw.get("pageIndex")
        if values is None or len(values) != 1:
            raise ValueError("org.go institution-chart URL requires one pageIndex")
        try:
            page_index = int(values[0])
        except ValueError:
            raise ValueError("pageIndex must be an integer") from None
        if page_index < 1:
            raise ValueError("pageIndex must be >= 1")
        return page_index

    def fetch(self, url: str) -> ConnectorDocument:
        page_index = self._validated_query(url)
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.BASE_URL, params={"pageIndex": page_index})
                response.raise_for_status()
                body = response.text
        except httpx.HTTPError:
            raise OrgGoTopLevelOrganizationError(
                "org.go institution-chart request failed"
            ) from None
        page = self.parse_page_body(body)
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="행정안전부",
            published_at=None,
            body=body,
            metadata={
                "source_contract": "orggo_top_level_organization_list_v1",
                "page_index": str(page_index),
                "row_count": str(len(page.organizations)),
                "total_count": str(page.total_count),
            },
        )


    @classmethod
    def parse_page_body(cls, body: str) -> OrgGoTopLevelOrganizationPage:
        parser = _OrgGoListParser()
        parser.feed(body)
        parser.close()
        if parser._current is not None:
            raise OrgGoTopLevelOrganizationError(
                "org.go subject row is not closed"
            )
        text = " ".join(part.strip() for part in parser.text_parts if part.strip())
        counts = {int(value.replace(",", "")) for value in _COUNT_RE.findall(text)}
        if len(counts) != 1:
            raise OrgGoTopLevelOrganizationError(
                "org.go institution-chart total count is unavailable or ambiguous"
            )
        total_count = counts.pop()
        if total_count < 1:
            raise OrgGoTopLevelOrganizationError(
                "org.go institution-chart total count must be positive"
            )

        records: list[OrgGoTopLevelOrganizationRecord] = []
        seen_codes: set[str] = set()
        seen_locators: set[tuple[str, str]] = set()
        for name, category, org_code, chart_id in parser.rows:
            if not name or not category:
                raise OrgGoTopLevelOrganizationError(
                    "org.go institution-chart row lacks a required label"
                )
            if org_code in seen_codes:
                raise OrgGoTopLevelOrganizationError(
                    "org.go institution-chart page contains duplicate orgCode"
                )
            locator = (org_code, chart_id)
            if locator in seen_locators:
                raise OrgGoTopLevelOrganizationError(
                    "org.go institution-chart page contains duplicate detail locator"
                )
            seen_codes.add(org_code)
            seen_locators.add(locator)
            records.append(
                OrgGoTopLevelOrganizationRecord(
                    organization_name=name,
                    category=category,
                    org_code=org_code,
                    chart_id=chart_id,
                )
            )
        if len(records) > total_count:
            raise OrgGoTopLevelOrganizationError(
                "org.go institution-chart page exceeds provider total count"
            )
        return OrgGoTopLevelOrganizationPage(tuple(records), total_count)

    @classmethod
    def parse_organizations(
        cls, document: ConnectorDocument
    ) -> list[OrgGoTopLevelOrganizationRecord]:
        return list(cls.parse_page_body(document.body).organizations)
