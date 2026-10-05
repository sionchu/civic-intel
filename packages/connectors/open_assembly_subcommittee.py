from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from .base import Connector, ConnectorDocument
from .open_assembly import AssemblyApiError, MissingAssemblyApiKey


@dataclass(frozen=True)
class AssemblySubcommitteeReviewRecord:
    assembly_age: int
    bill_no: str
    bill_id: str
    committee_id: str
    committee_name: str
    subcommittee_name: str | None
    present_session: str | None
    present_degree: str | None
    process_session: str | None
    process_degree: str | None
    referral_date: date | None
    present_date: date | None
    process_date: date | None
    process_result: str | None
    direct_referral: bool | None
    review_note: str | None


class OpenAssemblySubcommitteeReviewConnector(Connector):
    API_CODE = "TVBPMCONFINFO"
    BASE_URL = f"https://open.assembly.go.kr/portal/openapi/{API_CODE}"
    HOST = "open.assembly.go.kr"
    PATH = f"/portal/openapi/{API_CODE}"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"Type", "pIndex", "pSize", "AGE", "BILL_NO", "BILL_ID", "ENROLL_TYPE"}
    )
    SAFE_FIELDS: ClassVar[tuple[str, ...]] = (
        "AGE",
        "BILL_NO",
        "BILL_ID",
        "COMMITTEE_ID",
        "COMMITTEE_NAME",
        "SUB_COMMITTEE_NAME",
        "PRESENT_SESSION",
        "PRESENT_CHA",
        "PROC_SESSION",
        "PROC_CHA",
        "SUBMIT_DT",
        "PRESENT_DT",
        "PROC_DT",
        "PROC_RESULT_CD",
        "ENROLL_TYPE",
        "CONF_BIGO",
    )

    def __init__(
        self,
        *,
        assembly_age: int,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        bill_no: str | None = None,
        bill_id: str | None = None,
        direct_referral: str | None = None,
        sample_mode: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if assembly_age < 1:
            raise ValueError("assembly_age must be >= 1")
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if sample_mode and (page_index != 1 or page_size != 5):
            raise ValueError("official sample mode requires page_index=1 and page_size=5")
        normalized_referral = (
            direct_referral.strip().upper() if direct_referral is not None else None
        )
        if normalized_referral not in {None, "", "Y", "N"}:
            raise ValueError("direct_referral must be Y or N")
        self.assembly_age = assembly_age
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.bill_no = bill_no.strip() if bill_no else None
        self.bill_id = bill_id.strip() if bill_id else None
        self.direct_referral = normalized_referral or None
        self.sample_mode = sample_mode
        self._transport = transport

    @property
    def has_filters(self) -> bool:
        return any((self.bill_no, self.bill_id, self.direct_referral))

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
            "AGE": str(self.assembly_age),
        }
        if self.bill_no:
            params["BILL_NO"] = self.bill_no
        if self.bill_id:
            params["BILL_ID"] = self.bill_id
        if self.direct_referral:
            params["ENROLL_TYPE"] = self.direct_referral
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported National Assembly subcommittee-review API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        lowered = {key.casefold() for key in raw}
        if lowered & {"key", "authkey", "servicekey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported National Assembly subcommittee-review query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        age = query.get("AGE", "")
        if not age.isdigit() or int(age) < 1:
            raise ValueError("AGE is required for National Assembly subcommittee-review API")
        try:
            page_index = int(query.get("pIndex", "1"))
            page_size = int(query.get("pSize", "100"))
        except ValueError:
            raise ValueError("pIndex and pSize must be integers") from None
        if page_index < 1 or not 1 <= page_size <= 1000:
            raise ValueError("invalid Open Assembly pagination")
        referral = query.get("ENROLL_TYPE")
        if referral is not None and referral.upper() not in {"Y", "N"}:
            raise ValueError("ENROLL_TYPE must be Y or N")
        return query

    @classmethod
    def _response_parts(
        cls, payload: dict
    ) -> tuple[list[dict], int | None, str | None]:
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError(
                "National Assembly subcommittee-review API returned a malformed response"
            )
        total_count: int | None = None
        result_code: str | None = None
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
                    raise AssemblyApiError(
                        "National Assembly subcommittee-review API returned a malformed row"
                    )
                rows.extend(candidate_rows)
        if result_code == "INFO-200":
            return [], 0 if total_count is None else total_count, result_code
        if result_code not in {None, "", "INFO-000", "DATA-000"}:
            raise AssemblyApiError(
                f"National Assembly subcommittee-review API returned {result_code}"
            )
        return rows, total_count, result_code

    @classmethod
    def _safe_payload(
        cls,
        rows: list[dict],
        total_count: int | None,
        result_code: str | None,
    ) -> dict[str, object]:
        safe_rows = [
            {key: row.get(key) for key in cls.SAFE_FIELDS}
            for row in rows
        ]
        head: list[dict[str, object]] = []
        if total_count is not None:
            head.append({"list_total_count": total_count})
        head.append(
            {
                "RESULT": {
                    "CODE": result_code or "INFO-000",
                    "MESSAGE": "sanitized provider response",
                }
            }
        )
        return {cls.API_CODE: [{"head": head}, {"row": safe_rows}]}

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        if self.sample_mode and (
            query.get("pIndex", "1") != "1" or query.get("pSize", "5") != "5"
        ):
            raise ValueError("official sample mode requires page_index=1 and page_size=5")
        if int(query["AGE"]) != self.assembly_age:
            raise ValueError("discovered AGE does not match connector assembly_age")

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
                response = client.get(self.BASE_URL, params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise AssemblyApiError(
                "National Assembly subcommittee-review API request failed"
            ) from None

        if not isinstance(payload, dict):
            raise AssemblyApiError(
                "National Assembly subcommittee-review API returned a malformed response"
            )
        rows, total_count, result_code = self._response_parts(payload)
        safe_payload = self._safe_payload(rows, total_count, result_code)
        metadata = {
            "api_code": self.API_CODE,
            "assembly_age": query["AGE"],
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "100"),
            "row_count": str(len(rows)),
            "list_total_count": "" if total_count is None else str(total_count),
            "result_code": result_code or "",
            "sample_mode": str(self.sample_mode).lower(),
        }
        for key in ("BILL_NO", "BILL_ID", "ENROLL_TYPE"):
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title="국회 국회사무처_소위 심사정보(법률안)",
            publisher="국회 국회사무처",
            published_at=None,
            body=json.dumps(safe_payload, ensure_ascii=False, sort_keys=True),
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
    def _required(cls, row: dict, key: str) -> str:
        value = cls._optional(row, key)
        if value is None:
            raise AssemblyApiError(
                f"National Assembly subcommittee-review row lacks {key}"
            )
        return value

    @classmethod
    def _date(cls, row: dict, key: str) -> date | None:
        value = cls._optional(row, key)
        if value is None:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise AssemblyApiError(
                f"National Assembly subcommittee-review row has invalid {key}"
            ) from None

    @classmethod
    def _direct_referral(cls, row: dict) -> bool | None:
        value = cls._optional(row, "ENROLL_TYPE")
        if value is None:
            return None
        normalized = value.upper()
        if normalized == "Y":
            return True
        if normalized == "N":
            return False
        raise AssemblyApiError(
            "National Assembly subcommittee-review row has invalid ENROLL_TYPE"
        )

    def parse_reviews(
        self, document: ConnectorDocument
    ) -> tuple[AssemblySubcommitteeReviewRecord, ...]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError(
                "National Assembly subcommittee-review document is not valid JSON"
            ) from None
        if not isinstance(payload, dict):
            raise AssemblyApiError(
                "National Assembly subcommittee-review document is malformed"
            )
        rows, _, _ = self._response_parts(payload)
        records: list[AssemblySubcommitteeReviewRecord] = []
        for row in rows:
            age_text = self._required(row, "AGE")
            if not age_text.isdigit() or int(age_text) != self.assembly_age:
                raise AssemblyApiError(
                    "National Assembly subcommittee-review row AGE is inconsistent"
                )
            records.append(
                AssemblySubcommitteeReviewRecord(
                    assembly_age=int(age_text),
                    bill_no=self._required(row, "BILL_NO"),
                    bill_id=self._required(row, "BILL_ID"),
                    committee_id=self._required(row, "COMMITTEE_ID"),
                    committee_name=self._required(row, "COMMITTEE_NAME"),
                    subcommittee_name=self._optional(row, "SUB_COMMITTEE_NAME"),
                    present_session=self._optional(row, "PRESENT_SESSION"),
                    present_degree=self._optional(row, "PRESENT_CHA"),
                    process_session=self._optional(row, "PROC_SESSION"),
                    process_degree=self._optional(row, "PROC_CHA"),
                    referral_date=self._date(row, "SUBMIT_DT"),
                    present_date=self._date(row, "PRESENT_DT"),
                    process_date=self._date(row, "PROC_DT"),
                    process_result=self._optional(row, "PROC_RESULT_CD"),
                    direct_referral=self._direct_referral(row),
                    review_note=self._optional(row, "CONF_BIGO"),
                )
            )
        return tuple(records)
