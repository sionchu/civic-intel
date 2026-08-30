from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class AssemblyApiError(RuntimeError):
    pass


class MissingAssemblyApiKey(AssemblyApiError):
    pass


@dataclass(frozen=True)
class AssemblyMemberRecord:
    member_code: str
    name_ko: str
    name_hanja: str | None = None
    name_en: str | None = None
    birth_date: date | None = None
    party: str | None = None
    district: str | None = None
    reelection: str | None = None
    election_type: str | None = None
    committees: str | None = None


POLICY_ID = UUID("11000000-0000-0000-0000-000000000001")


def national_assembly_member_policy() -> SourcePolicy:
    """Reviewed policy for the National Assembly member-information Open API.

    The official public-data catalog states that the API is free and has no license-use
    restriction. V0 still avoids retaining the raw response because member rows may carry
    contact fields that are unnecessary for identity resolution.
    """

    reviewed_at = datetime(2026, 8, 30, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="open.assembly.go.kr",
        source_class="official_open_api",
        collection_mode=SourceCollectionMode.API,
        can_fetch=True,
        can_store_metadata=True,
        can_store_fulltext=False,
        can_send_to_ai=False,
        can_show_excerpt=False,
        can_commercialize=True,
        terms_checked_at=reviewed_at,
        license="이용허락범위 제한 없음",
        rate_limit="Provider-controlled; development auto-approval, operation review",
        policy_note=(
            "Reviewed against data.go.kr dataset 15126133 on 2026-08-30. "
            "Raw member responses are not retained in V0 as a data-minimization choice."
        ),
    )


class OpenAssemblyMemberConnector(Connector):
    API_CODE = "nwvrqwxyaytdsfvhu"
    BASE_URL = f"https://open.assembly.go.kr/portal/openapi/{API_CODE}"
    HOST = "open.assembly.go.kr"
    PATH = f"/portal/openapi/{API_CODE}"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"Type", "pIndex", "pSize", "HG_NM", "POLY_NM", "ORIG_NM"}
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        name: str | None = None,
        party: str | None = None,
        district: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.name = name
        self.party = party
        self.district = district
        self._transport = transport

    def _credential(self) -> str:
        value = self._api_key or os.getenv("ASSEMBLY_API_KEY")
        if not value:
            raise MissingAssemblyApiKey("ASSEMBLY_API_KEY is required for live fetch")
        return value

    def discover(self) -> list[str]:
        params: dict[str, str] = {
            "Type": "json",
            "pIndex": str(self.page_index),
            "pSize": str(self.page_size),
        }
        if self.name:
            params["HG_NM"] = self.name
        if self.party:
            params["POLY_NM"] = self.party
        if self.district:
            params["ORIG_NM"] = self.district
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported National Assembly API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if "KEY" in raw or "authKey" in raw:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported National Assembly API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        return query

    @staticmethod
    def _redact_credentials(value):
        if isinstance(value, dict):
            return {
                key: OpenAssemblyMemberConnector._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"key", "authkey"}
            }
        if isinstance(value, list):
            return [OpenAssemblyMemberConnector._redact_credentials(item) for item in value]
        return value

    @classmethod
    def _response_parts(cls, payload: dict) -> tuple[list[dict], int | None]:
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError("National Assembly member API returned a malformed response")

        result_code: str | None = None
        total_count: int | None = None
        rows: list[dict] = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            head = block.get("head")
            if isinstance(head, list):
                for item in head:
                    if not isinstance(item, dict):
                        continue
                    if "list_total_count" in item:
                        try:
                            total_count = int(item["list_total_count"])
                        except (TypeError, ValueError):
                            total_count = None
                    result = item.get("RESULT")
                    if isinstance(result, dict):
                        result_code = str(result.get("CODE") or "")
            candidate_rows = block.get("row")
            if isinstance(candidate_rows, list):
                rows.extend(item for item in candidate_rows if isinstance(item, dict))

        if result_code not in {None, "", "INFO-000", "DATA-000"}:
            raise AssemblyApiError(f"National Assembly member API returned {result_code}")
        return rows, total_count

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = query | {"KEY": self._credential()}
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.BASE_URL, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise AssemblyApiError("National Assembly member API request failed") from None

        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly member API returned a malformed response")
        payload = self._redact_credentials(payload)
        rows, total_count = self._response_parts(payload)
        metadata = {
            "api_code": self.API_CODE,
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "10"),
            "row_count": str(len(rows)),
            "list_total_count": "" if total_count is None else str(total_count),
        }
        for key in ("HG_NM", "POLY_NM", "ORIG_NM"):
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title="국회 국회사무처_국회의원 정보 통합 API",
            publisher="국회 국회사무처",
            published_at=None,
            body=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            metadata=metadata,
        )

    @staticmethod
    def _optional(row: dict, key: str) -> str | None:
        value = row.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @classmethod
    def _birth_date(cls, row: dict) -> date | None:
        value = cls._optional(row, "BTH_DATE")
        if not value:
            return None
        normalized = value.replace(".", "-").replace("/", "-")
        try:
            if len(normalized) == 10:
                return date.fromisoformat(normalized)
            if len(normalized) == 8 and normalized.isdigit():
                return date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:8]))
        except ValueError:
            return None
        return None

    @classmethod
    def parse_members(cls, document: ConnectorDocument) -> list[AssemblyMemberRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError("National Assembly member document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly member document is malformed")
        rows, _ = cls._response_parts(payload)
        members: list[AssemblyMemberRecord] = []
        for row in rows:
            member_code = cls._optional(row, "MONA_CD")
            name_ko = cls._optional(row, "HG_NM")
            if not member_code or not name_ko:
                raise AssemblyApiError("National Assembly member row lacks identity anchors")
            members.append(
                AssemblyMemberRecord(
                    member_code=member_code,
                    name_ko=name_ko,
                    name_hanja=cls._optional(row, "HJ_NM"),
                    name_en=cls._optional(row, "ENG_NM"),
                    birth_date=cls._birth_date(row),
                    party=cls._optional(row, "POLY_NM"),
                    district=cls._optional(row, "ORIG_NM"),
                    reelection=cls._optional(row, "REELE_GBN_NM"),
                    election_type=cls._optional(row, "ELECT_GBN_NM"),
                    committees=cls._optional(row, "CMITS"),
                )
            )
        return members
