from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument
from .open_assembly import (
    POLICY_ID as ASSEMBLY_SOURCE_POLICY_ID,
    AssemblyApiError,
    MissingAssemblyApiKey,
)


@dataclass(frozen=True)
class AssemblyScheduleRecord:
    schedule_date: date
    schedule_kind: str | None
    schedule_time: str | None
    committee_name: str | None
    content: str | None
    place: str | None
    session: str | None
    degree: str | None

    @property
    def is_gukgam_candidate(self) -> bool:
        text = " ".join(
            value
            for value in (self.schedule_kind, self.content)
            if value is not None
        )
        return "국정감사" in "".join(text.split())


POLICY_ID = ASSEMBLY_SOURCE_POLICY_ID


def national_assembly_schedule_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 9, 19, tzinfo=UTC)
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
            "Provider-controlled traffic; development auto-approval, "
            "operation review approval"
        ),
        policy_note=(
            "Reviewed 2026-09-19 against data.go.kr dataset 15126132 "
            "(국회 국회사무처_국회일정 통합 API). This lane is schedule discovery only. "
            "It does not establish audited-organization or witness identity and stores no "
            "raw API fulltext."
        ),
    )


class OpenAssemblyScheduleConnector(Connector):
    """Bounded Open Assembly schedule reader for Gukgam discovery candidates."""

    API_CODE = "ALLSCHEDULE"
    BASE_URL = f"https://open.assembly.go.kr/portal/openapi/{API_CODE}"
    HOST = "open.assembly.go.kr"
    PATH = f"/portal/openapi/{API_CODE}"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"Type", "pIndex", "pSize", "SCH_DT", "CMIT_NM"}
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        schedule_date: date | None = None,
        committee: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.schedule_date = schedule_date
        self.committee = committee
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
        if self.schedule_date is not None:
            params["SCH_DT"] = self.schedule_date.strftime("%Y%m%d")
        if self.committee:
            params["CMIT_NM"] = self.committee
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != cls.HOST
            or parsed.path != cls.PATH
        ):
            raise ValueError("unsupported National Assembly schedule API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if "KEY" in raw or "authKey" in raw:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported National Assembly schedule API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        schedule_date = query.get("SCH_DT")
        if schedule_date is not None and (
            len(schedule_date) != 8 or not schedule_date.isdigit()
        ):
            raise ValueError("SCH_DT must use YYYYMMDD")
        return query

    @staticmethod
    def _redact_credentials(value):
        if isinstance(value, dict):
            return {
                key: OpenAssemblyScheduleConnector._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"key", "authkey"}
            }
        if isinstance(value, list):
            return [
                OpenAssemblyScheduleConnector._redact_credentials(item)
                for item in value
            ]
        return value

    @classmethod
    def _response_parts(
        cls,
        payload: dict,
    ) -> tuple[list[dict], int | None, str | None]:
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError(
                "National Assembly schedule API returned a malformed response"
            )

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

        if result_code in {"DATA-000", "INFO-200"}:
            return [], 0 if total_count is None else total_count, result_code
        if result_code not in {None, "", "INFO-000"}:
            raise AssemblyApiError(
                f"National Assembly schedule API returned {result_code}"
            )
        return rows, total_count, result_code

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = query | {"KEY": self._credential()}
        headers = {
            "User-Agent": os.getenv(
                "CIVIC_HTTP_USER_AGENT",
                "CivicIntel/0.1 (+contact@example.invalid)",
            )
        }
        try:
            with httpx.Client(
                transport=self._transport,
                timeout=15,
                headers=headers,
            ) as client:
                response = client.get(self.BASE_URL, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise AssemblyApiError(
                "National Assembly schedule API request failed"
            ) from None

        if not isinstance(payload, dict):
            raise AssemblyApiError(
                "National Assembly schedule API returned a malformed response"
            )
        payload = self._redact_credentials(payload)
        rows, total_count, result_code = self._response_parts(payload)
        metadata = {
            "api_code": self.API_CODE,
            "source_contract": "national_assembly_schedule_v1",
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "10"),
            "row_count": str(len(rows)),
            "list_total_count": "" if total_count is None else str(total_count),
            "result_code": result_code or "",
        }
        for key in ("SCH_DT", "CMIT_NM"):
            if key in query:
                metadata[key] = query[key]

        return ConnectorDocument(
            url=url,
            title="국회 국회사무처_국회일정 통합 API",
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
    def _schedule_date(cls, row: dict) -> date:
        raw = cls._optional(row, "SCH_DT")
        if raw is None:
            raise AssemblyApiError("National Assembly schedule row lacks SCH_DT")
        normalized = raw.replace(".", "").replace("-", "").replace("/", "")
        if len(normalized) != 8 or not normalized.isdigit():
            raise AssemblyApiError("National Assembly schedule row has invalid SCH_DT")
        try:
            return date(
                int(normalized[:4]),
                int(normalized[4:6]),
                int(normalized[6:8]),
            )
        except ValueError:
            raise AssemblyApiError(
                "National Assembly schedule row has invalid SCH_DT"
            ) from None

    @classmethod
    def parse_schedules(
        cls,
        document: ConnectorDocument,
    ) -> list[AssemblyScheduleRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError(
                "National Assembly schedule document is not valid JSON"
            ) from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly schedule document is malformed")

        rows, _, _ = cls._response_parts(payload)
        records: list[AssemblyScheduleRecord] = []
        for row in rows:
            schedule_kind = cls._optional(row, "SCH_KIND")
            content = cls._optional(row, "SCH_CN")
            if schedule_kind is None and content is None:
                raise AssemblyApiError(
                    "National Assembly schedule row lacks schedule semantics"
                )
            records.append(
                AssemblyScheduleRecord(
                    schedule_date=cls._schedule_date(row),
                    schedule_kind=schedule_kind,
                    schedule_time=cls._optional(row, "SCH_TM"),
                    committee_name=cls._optional(row, "CMIT_NM"),
                    content=content,
                    place=cls._optional(row, "EV_PLC"),
                    session=cls._optional(row, "CONF_SESS"),
                    degree=cls._optional(row, "CONF_DGR"),
                )
            )
        return records

    @staticmethod
    def gukgam_candidates(
        records: list[AssemblyScheduleRecord],
    ) -> list[AssemblyScheduleRecord]:
        return [record for record in records if record.is_gukgam_candidate]
