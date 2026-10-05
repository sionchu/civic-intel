from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument
from .open_assembly import POLICY_ID as ASSEMBLY_SOURCE_POLICY_ID
from .open_assembly import AssemblyApiError, MissingAssemblyApiKey

POLICY_ID = ASSEMBLY_SOURCE_POLICY_ID


def national_assembly_committee_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 10, 5, tzinfo=UTC)
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
        rate_limit=(
            "Provider service pages show request limit 200000; normal use requires an issued "
            "Open Assembly API key. Public no-key sample mode is page 1 / 5 rows only."
        ),
        policy_note=(
            "Reviewed 2026-10-05 against the official Open Assembly committee-status "
            "nxrvzonlafugpqjuh and committee-member nktulghcadyhmiqxi service pages, "
            "data.go.kr dataset 15126035, and the Open API terms. Attribution to 열린국회정보 "
            "is required. Civic Intel discards member phone, email, room and staff fields before "
            "normalized connector output. This L2 review does not authorize L3 current-roster "
            "enumeration until an issued key and current-scope reconciliation are proven."
        ),
    )


@dataclass(frozen=True)
class AssemblyCommitteeStatusRecord:
    committee_division_code: str
    committee_division_name: str
    committee_code: str
    committee_name: str
    chair_text: str | None
    secretary_text: str | None
    authorized_count: int
    current_count: int
    non_negotiation_group_count: int
    negotiation_group_count: int


@dataclass(frozen=True)
class AssemblyCommitteeMemberRecord:
    committee_code: str
    committee_name: str
    role: str
    member_code: str
    name_ko: str
    name_hanja: str | None
    district: str | None
    party: str | None


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required(row: dict, key: str, *, label: str) -> str:
    value = _optional(row, key)
    if value is None:
        raise AssemblyApiError(f"{label} row lacks required field {key}")
    return value


def _required_int(row: dict, key: str, *, label: str) -> int:
    value = row.get(key)
    if value is None:
        raise AssemblyApiError(f"{label} row lacks required integer field {key}")
    try:
        return int(str(value))
    except ValueError:
        raise AssemblyApiError(f"{label} row has invalid integer field {key}") from None


def _response_parts(
    payload: dict,
    *,
    api_code: str,
    label: str,
) -> tuple[list[dict], int | None, str | None]:
    blocks = payload.get(api_code)
    if not isinstance(blocks, list) or not blocks:
        raise AssemblyApiError(f"{label} API returned a malformed response")

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
            if any(not isinstance(item, dict) for item in candidate_rows):
                raise AssemblyApiError(f"{label} API returned a malformed row")
            rows.extend(candidate_rows)

    if result_code not in {None, "", "INFO-000", "DATA-000"}:
        raise AssemblyApiError(f"{label} API returned {result_code}")
    return rows, total_count, result_code


def _sanitized_payload(
    *,
    api_code: str,
    total_count: int | None,
    result_code: str | None,
    rows: list[dict[str, object]],
) -> dict[str, object]:
    head: list[dict[str, object]] = []
    if total_count is not None:
        head.append({"list_total_count": total_count})
    head.append({"RESULT": {"CODE": result_code or "INFO-000"}})
    return {api_code: [{"head": head}, {"row": rows}]}


class _AssemblyCommitteeConnector(Connector):
    API_CODE: ClassVar[str]
    SOURCE_LABEL: ClassVar[str]
    TITLE: ClassVar[str]
    ALLOWED_FILTERS: ClassVar[frozenset[str]]
    SAFE_FIELDS: ClassVar[tuple[str, ...]]

    HOST = "open.assembly.go.kr"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        sample_mode: bool = False,
        filters: dict[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if sample_mode and (page_index != 1 or page_size != 5):
            raise ValueError("official sample mode requires page_index=1 and page_size=5")
        supplied_filters = filters or {}
        unknown = set(supplied_filters) - self.ALLOWED_FILTERS
        if unknown:
            raise ValueError(f"unsupported {self.SOURCE_LABEL} filter")
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.sample_mode = sample_mode
        self.filters = {
            key: str(value).strip()
            for key, value in supplied_filters.items()
            if str(value).strip()
        }
        self._transport = transport

    @property
    def path(self) -> str:
        return f"/portal/openapi/{self.API_CODE}"

    @property
    def base_url(self) -> str:
        return f"https://{self.HOST}{self.path}"

    def _credential(self) -> str | None:
        if self.sample_mode:
            return None
        value = self._api_key or os.getenv("ASSEMBLY_API_KEY")
        if not value:
            raise MissingAssemblyApiKey("ASSEMBLY_API_KEY is required for live fetch")
        return value

    def discover(self) -> list[str]:
        params = {
            "Type": "json",
            "pIndex": str(self.page_index),
            "pSize": str(self.page_size),
            **self.filters,
        }
        return [f"{self.base_url}?{urlencode(params)}"]

    def _validated_query(self, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != self.HOST or parsed.path != self.path:
            raise ValueError(f"unsupported {self.SOURCE_LABEL} API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        lowered = {key.casefold() for key in raw}
        if lowered & {"key", "authkey", "servicekey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        allowed = {"Type", "pIndex", "pSize"} | set(self.ALLOWED_FILTERS)
        if set(raw) - allowed:
            raise ValueError(f"unsupported {self.SOURCE_LABEL} API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        try:
            page_index = int(query.get("pIndex", "1"))
            page_size = int(query.get("pSize", "100"))
        except ValueError:
            raise ValueError("pIndex and pSize must be integers") from None
        if page_index < 1 or not 1 <= page_size <= 1000:
            raise ValueError("invalid Open Assembly pagination")
        if self.sample_mode and (page_index != 1 or page_size != 5):
            raise ValueError("official sample mode requires page_index=1 and page_size=5")
        return query

    def _safe_row(self, row: dict) -> dict[str, object]:
        return {key: row.get(key) for key in self.SAFE_FIELDS}

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = dict(query)
        credential = self._credential()
        if credential is not None:
            request_params["KEY"] = credential

        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT", "CivicIntel/0.1 (+contact@example.invalid)"
            )
        }
        try:
            with httpx.Client(transport=self._transport, timeout=15, headers=headers) as client:
                response = client.get(self.base_url, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise AssemblyApiError(f"{self.SOURCE_LABEL} API request failed") from None

        if not isinstance(payload, dict):
            raise AssemblyApiError(f"{self.SOURCE_LABEL} API returned a malformed response")
        rows, total_count, result_code = _response_parts(
            payload,
            api_code=self.API_CODE,
            label=self.SOURCE_LABEL,
        )
        safe_rows = [self._safe_row(row) for row in rows]
        sanitized = _sanitized_payload(
            api_code=self.API_CODE,
            total_count=total_count,
            result_code=result_code,
            rows=safe_rows,
        )
        metadata = {
            "api_code": self.API_CODE,
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "100"),
            "row_count": str(len(safe_rows)),
            "list_total_count": "" if total_count is None else str(total_count),
            "sample_mode": str(self.sample_mode).lower(),
        }
        for key in self.ALLOWED_FILTERS:
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="국회 국회사무처",
            published_at=None,
            body=json.dumps(sanitized, ensure_ascii=False, sort_keys=True),
            metadata=metadata,
        )


class OpenAssemblyCommitteeStatusConnector(_AssemblyCommitteeConnector):
    API_CODE = "nxrvzonlafugpqjuh"
    SOURCE_LABEL = "National Assembly committee-status"
    TITLE = "국회 국회사무처_위원회 현황 정보"
    ALLOWED_FILTERS = frozenset(
        {"CMT_DIV_NM", "HR_DEPT_CD", "COMMITTEE_NAME", "HG_NM", "HG_NM_LIST"}
    )
    SAFE_FIELDS = (
        "CMT_DIV_CD",
        "CMT_DIV_NM",
        "HR_DEPT_CD",
        "COMMITTEE_NAME",
        "HG_NM",
        "HG_NM_LIST",
        "LIMIT_CNT",
        "CURR_CNT",
        "POLY99_CNT",
        "POLY_CNT",
    )

    @classmethod
    def parse_statuses(
        cls,
        document: ConnectorDocument,
    ) -> tuple[AssemblyCommitteeStatusRecord, ...]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError("committee-status document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("committee-status document is malformed")
        rows, _, _ = _response_parts(
            payload,
            api_code=cls.API_CODE,
            label=cls.SOURCE_LABEL,
        )
        records = []
        for row in rows:
            records.append(
                AssemblyCommitteeStatusRecord(
                    committee_division_code=_required(
                        row, "CMT_DIV_CD", label=cls.SOURCE_LABEL
                    ),
                    committee_division_name=_required(
                        row, "CMT_DIV_NM", label=cls.SOURCE_LABEL
                    ),
                    committee_code=_required(
                        row, "HR_DEPT_CD", label=cls.SOURCE_LABEL
                    ),
                    committee_name=_required(
                        row, "COMMITTEE_NAME", label=cls.SOURCE_LABEL
                    ),
                    chair_text=_optional(row, "HG_NM"),
                    secretary_text=_optional(row, "HG_NM_LIST"),
                    authorized_count=_required_int(
                        row, "LIMIT_CNT", label=cls.SOURCE_LABEL
                    ),
                    current_count=_required_int(
                        row, "CURR_CNT", label=cls.SOURCE_LABEL
                    ),
                    non_negotiation_group_count=_required_int(
                        row, "POLY99_CNT", label=cls.SOURCE_LABEL
                    ),
                    negotiation_group_count=_required_int(
                        row, "POLY_CNT", label=cls.SOURCE_LABEL
                    ),
                )
            )
        return tuple(records)


class OpenAssemblyCommitteeMemberConnector(_AssemblyCommitteeConnector):
    API_CODE = "nktulghcadyhmiqxi"
    SOURCE_LABEL = "National Assembly committee-member"
    TITLE = "국회 국회사무처_위원회 위원 명단"
    ALLOWED_FILTERS = frozenset(
        {
            "DEPT_CD",
            "DEPT_NM",
            "JOB_RES_NM",
            "HG_NM",
            "ORIG_NM",
            "POLY_NM",
            "MONA_CD",
        }
    )
    SAFE_FIELDS = (
        "DEPT_CD",
        "DEPT_NM",
        "JOB_RES_NM",
        "HG_NM",
        "ORIG_NM",
        "POLY_NM",
        "HJ_NM",
        "MONA_CD",
    )

    @classmethod
    def parse_memberships(
        cls,
        document: ConnectorDocument,
    ) -> tuple[AssemblyCommitteeMemberRecord, ...]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError("committee-member document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("committee-member document is malformed")
        rows, _, _ = _response_parts(
            payload,
            api_code=cls.API_CODE,
            label=cls.SOURCE_LABEL,
        )
        records = []
        for row in rows:
            records.append(
                AssemblyCommitteeMemberRecord(
                    committee_code=_required(row, "DEPT_CD", label=cls.SOURCE_LABEL),
                    committee_name=_required(row, "DEPT_NM", label=cls.SOURCE_LABEL),
                    role=_required(row, "JOB_RES_NM", label=cls.SOURCE_LABEL),
                    member_code=_required(row, "MONA_CD", label=cls.SOURCE_LABEL),
                    name_ko=_required(row, "HG_NM", label=cls.SOURCE_LABEL),
                    name_hanja=_optional(row, "HJ_NM"),
                    district=_optional(row, "ORIG_NM"),
                    party=_optional(row, "POLY_NM"),
                )
            )
        return tuple(records)
