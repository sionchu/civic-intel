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
from .open_assembly import AssemblyApiError, MissingAssemblyApiKey


@dataclass(frozen=True)
class AssemblyBillRecord:
    bill_id: str
    bill_name: str
    assembly_age: int
    bill_no: str | None = None
    proposed_date: date | None = None
    committee: str | None = None
    committee_id: str | None = None
    process_result: str | None = None
    proposer_summary: str | None = None
    representative_proposers: tuple[str, ...] = ()
    co_proposers: tuple[str, ...] = ()
    representative_proposer_codes: tuple[str, ...] | None = None
    co_proposer_codes: tuple[str, ...] | None = None
    detail_url: str | None = None

    @property
    def role_code_fields_complete(self) -> bool:
        return self.representative_proposer_codes is not None and self.co_proposer_codes is not None

    def role_for_code(self, member_code: str) -> str | None:
        target = member_code.strip()
        if self.representative_proposer_codes is not None and target in self.representative_proposer_codes:
            return "LEAD"
        if self.co_proposer_codes is not None and target in self.co_proposer_codes:
            return "CO_SPONSOR"
        return None

    def role_for(self, person_name: str) -> str | None:
        """Legacy display-name helper. Exact participation staging must use role_for_code()."""

        target = _normalize_person_name(person_name)
        if target in {_normalize_person_name(item) for item in self.representative_proposers}:
            return "LEAD"
        if target in {_normalize_person_name(item) for item in self.co_proposers}:
            return "CO_SPONSOR"
        return None


POLICY_ID = UUID("11000000-0000-0000-0000-000000000002")


def national_assembly_bill_policy() -> SourcePolicy:
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
            "Reviewed 2026-08-30 for National Assembly 의원 발의법률안 API "
            "nzmimeepazxkubdpn. V0 stages structured metadata and proposer-code fields only; "
            "no bill-detail HTML scraping."
        ),
    )


def _normalize_person_name(value: str) -> str:
    normalized = "".join(value.split())
    return normalized.removesuffix("의원")


def _names(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(name for item in str(value).split(",") if (name := str(item).strip()))


def _codes(row: dict, key: str, *, delimiter: str) -> tuple[str, ...] | None:
    """Return normalized codes; None means field missing or malformed, () means present/empty."""

    if key not in row:
        return None
    value = row.get(key)
    if value is None:
        return ()
    text = str(value).strip()
    if text in {"", "-"}:
        return ()
    unexpected = ";" if delimiter == "," else ","
    if unexpected in text:
        return None
    parts = text.split(delimiter)
    codes: list[str] = []
    for part in parts:
        code = part.strip()
        if not code or any(char.isspace() for char in code) or "," in code or ";" in code:
            return None
        if code not in codes:
            codes.append(code)
    return tuple(codes)


class OpenAssemblyBillConnector(Connector):
    API_CODE = "nzmimeepazxkubdpn"
    BASE_URL = f"https://open.assembly.go.kr/portal/openapi/{API_CODE}"
    HOST = "open.assembly.go.kr"
    PATH = f"/portal/openapi/{API_CODE}"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {
            "Type",
            "pIndex",
            "pSize",
            "AGE",
            "BILL_ID",
            "BILL_NO",
            "BILL_NAME",
            "COMMITTEE",
            "COMMITTEE_ID",
            "PROC_RESULT",
            "PROPOSER",
        }
    )

    def __init__(
        self,
        *,
        assembly_age: int,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        bill_id: str | None = None,
        bill_no: str | None = None,
        bill_name: str | None = None,
        committee: str | None = None,
        committee_id: str | None = None,
        process_result: str | None = None,
        proposer: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if assembly_age < 1:
            raise ValueError("assembly_age must be >= 1")
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        self.assembly_age = assembly_age
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.bill_id = bill_id
        self.bill_no = bill_no
        self.bill_name = bill_name
        self.committee = committee
        self.committee_id = committee_id
        self.process_result = process_result
        self.proposer = proposer
        self._transport = transport

    @property
    def has_filters(self) -> bool:
        return any(
            value
            for value in (
                self.bill_id,
                self.bill_no,
                self.bill_name,
                self.committee,
                self.committee_id,
                self.process_result,
                self.proposer,
            )
        )

    def for_page(self, page_index: int) -> OpenAssemblyBillConnector:
        return OpenAssemblyBillConnector(
            assembly_age=self.assembly_age,
            api_key=self._api_key,
            page_index=page_index,
            page_size=self.page_size,
            bill_id=self.bill_id,
            bill_no=self.bill_no,
            bill_name=self.bill_name,
            committee=self.committee,
            committee_id=self.committee_id,
            process_result=self.process_result,
            proposer=self.proposer,
            transport=self._transport,
        )

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
            "AGE": str(self.assembly_age),
        }
        for key, value in (
            ("BILL_ID", self.bill_id),
            ("BILL_NO", self.bill_no),
            ("BILL_NAME", self.bill_name),
            ("COMMITTEE", self.committee),
            ("COMMITTEE_ID", self.committee_id),
            ("PROC_RESULT", self.process_result),
            ("PROPOSER", self.proposer),
        ):
            if value:
                params[key] = value
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported National Assembly bill API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if "KEY" in raw or "authKey" in raw:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported National Assembly bill API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        if not query.get("AGE"):
            raise ValueError("AGE is required for National Assembly bill API")
        return query

    @staticmethod
    def _redact_credentials(value):
        if isinstance(value, dict):
            return {
                key: OpenAssemblyBillConnector._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"key", "authkey"}
            }
        if isinstance(value, list):
            return [OpenAssemblyBillConnector._redact_credentials(item) for item in value]
        return value

    @classmethod
    def _response_parts(cls, payload: dict) -> tuple[list[dict], int | None, str | None]:
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError("National Assembly bill API returned a malformed response")

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

        if result_code == "INFO-200":
            return [], 0 if total_count is None else total_count, result_code
        if result_code not in {None, "", "INFO-000", "DATA-000"}:
            raise AssemblyApiError(f"National Assembly bill API returned {result_code}")
        return rows, total_count, result_code

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
            raise AssemblyApiError("National Assembly bill API request failed") from None

        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly bill API returned a malformed response")
        payload = self._redact_credentials(payload)
        rows, total_count, result_code = self._response_parts(payload)
        metadata = {
            "api_code": self.API_CODE,
            "assembly_age": query["AGE"],
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "100"),
            "row_count": str(len(rows)),
            "list_total_count": "" if total_count is None else str(total_count),
            "result_code": result_code or "",
        }
        for key in self.ALLOWED_QUERY - {"Type", "pIndex", "pSize", "AGE"}:
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title="국회 국회사무처_의원 발의법률안 API",
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
    def _proposal_date(cls, row: dict) -> date | None:
        value = cls._optional(row, "PROPOSE_DT")
        if not value:
            return None
        normalized = value.replace(".", "-").replace("/", "-")
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None

    @classmethod
    def parse_bills(cls, document: ConnectorDocument) -> list[AssemblyBillRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError("National Assembly bill document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly bill document is malformed")
        rows, _, _ = cls._response_parts(payload)
        bills: list[AssemblyBillRecord] = []
        for row in rows:
            bill_id = cls._optional(row, "BILL_ID")
            bill_name = cls._optional(row, "BILL_NAME")
            age_text = cls._optional(row, "AGE")
            if not bill_id or not bill_name or not age_text:
                raise AssemblyApiError("National Assembly bill row lacks required identity fields")
            try:
                age = int(age_text)
            except ValueError:
                raise AssemblyApiError("National Assembly bill row has invalid AGE") from None
            bills.append(
                AssemblyBillRecord(
                    bill_id=bill_id,
                    bill_no=cls._optional(row, "BILL_NO"),
                    bill_name=bill_name,
                    assembly_age=age,
                    proposed_date=cls._proposal_date(row),
                    committee=cls._optional(row, "COMMITTEE"),
                    committee_id=cls._optional(row, "COMMITTEE_ID"),
                    process_result=cls._optional(row, "PROC_RESULT"),
                    proposer_summary=cls._optional(row, "PROPOSER"),
                    representative_proposers=_names(row.get("RST_PROPOSER")),
                    co_proposers=_names(row.get("PUBL_PROPOSER")),
                    representative_proposer_codes=_codes(row, "RST_MONA_CD", delimiter=","),
                    co_proposer_codes=_codes(row, "PUBL_MONA_CD", delimiter=";"),
                    detail_url=cls._optional(row, "DETAIL_LINK"),
                )
            )
        return bills
