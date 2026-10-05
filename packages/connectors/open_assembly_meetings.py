from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import httpx

from .base import Connector, ConnectorDocument
from .open_assembly import AssemblyApiError, MissingAssemblyApiKey


@dataclass(frozen=True)
class AssemblyMeetingDetailRecord:
    meeting_id: str
    assembly_term: str
    session: str
    degree: str
    meeting_date: date
    meeting_kind: str
    committee_name: str
    subcommittee_name: str | None
    place: str | None
    start_time: str | None
    end_time: str | None
    duration: str | None
    personnel_hearing: bool | None
    public_hearing: bool | None
    hearing: bool | None
    joint_meeting: bool | None
    presidential_delegated_speech: bool | None
    presidential_policy_speech: bool | None
    foreign_guest_speech: bool | None
    minutes_download_url: str | None


@dataclass(frozen=True)
class AssemblyMeetingAgendaRecord:
    meeting_id: str
    assembly_term: str
    session: str
    degree: str
    agenda_no: int
    agenda_name: str
    agenda_level: int


@dataclass(frozen=True)
class AssemblyMeetingBillRecord:
    meeting_id: str
    assembly_term: str
    session: str
    degree: str
    bill_id: str
    bill_name: str
    link_url: str | None


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


def _date_value(row: dict, key: str, *, label: str) -> date:
    value = _required(row, key, label=label)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise AssemblyApiError(f"{label} row has invalid date field {key}") from None


def _yn(row: dict, key: str, *, label: str) -> bool | None:
    value = _optional(row, key)
    if value is None:
        return None
    normalized = value.upper()
    if normalized == "Y":
        return True
    if normalized == "N":
        return False
    raise AssemblyApiError(f"{label} row has invalid Y/N field {key}")


def _sanitized_url(value: str | None) -> str | None:
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise AssemblyApiError("National Assembly meeting row has unsafe linked URL")
    raw = parse_qs(parsed.query, keep_blank_values=True)
    clean = {
        key: values
        for key, values in raw.items()
        if key.casefold() not in {"key", "authkey", "servicekey"}
    }
    query_items: list[tuple[str, str]] = []
    for key, values in clean.items():
        for item in values:
            query_items.append((key, item))
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_items),
            "",
        )
    )


class _OpenAssemblyMeetingConnector(Connector):
    API_CODE: ClassVar[str]
    LABEL: ClassVar[str]
    TITLE: ClassVar[str]
    SAFE_FIELDS: ClassVar[tuple[str, ...]]
    EXTRA_FILTERS: ClassVar[frozenset[str]] = frozenset()

    HOST = "open.assembly.go.kr"

    def __init__(
        self,
        *,
        meeting_id: str,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        sample_mode: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        meeting_id = meeting_id.strip()
        if not meeting_id:
            raise ValueError("meeting_id is required")
        if page_index < 1:
            raise ValueError("page_index must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if sample_mode and (page_index != 1 or page_size != 5):
            raise ValueError("official sample mode requires page_index=1 and page_size=5")
        self.meeting_id = meeting_id
        self._api_key = api_key
        self.page_index = page_index
        self.page_size = page_size
        self.sample_mode = sample_mode
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

    def _query_params(self) -> dict[str, str]:
        return {
            "Type": "json",
            "pIndex": str(self.page_index),
            "pSize": str(self.page_size),
            "CONF_ID": self.meeting_id,
        }

    def discover(self) -> list[str]:
        return [f"{self.base_url}?{urlencode(self._query_params())}"]

    def _validated_query(self, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != self.HOST or parsed.path != self.path:
            raise ValueError(f"unsupported {self.LABEL} API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        lowered = {key.casefold() for key in raw}
        if lowered & {"key", "authkey", "servicekey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        allowed = {"Type", "pIndex", "pSize", "CONF_ID"} | set(self.EXTRA_FILTERS)
        if set(raw) - allowed:
            raise ValueError(f"unsupported {self.LABEL} API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        if query.get("CONF_ID", "").strip() != self.meeting_id:
            raise ValueError("CONF_ID does not match connector meeting_id")
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

    @classmethod
    def _response_parts(
        cls, payload: dict
    ) -> tuple[list[dict], int | None, str | None]:
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError(f"{cls.LABEL} API returned a malformed response")
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
                    raise AssemblyApiError(f"{cls.LABEL} API returned a malformed row")
                rows.extend(candidate_rows)
        if result_code == "INFO-200":
            return [], 0 if total_count is None else total_count, result_code
        if result_code not in {None, "", "INFO-000", "DATA-000"}:
            raise AssemblyApiError(f"{cls.LABEL} API returned {result_code}")
        return rows, total_count, result_code

    @classmethod
    def _safe_row(cls, row: dict) -> dict[str, object]:
        return {key: row.get(key) for key in cls.SAFE_FIELDS}

    @classmethod
    def _safe_payload(
        cls,
        rows: list[dict],
        total_count: int | None,
        result_code: str | None,
    ) -> dict[str, object]:
        safe_rows = [cls._safe_row(row) for row in rows]
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
            raise AssemblyApiError(f"{self.LABEL} API request failed") from None

        if not isinstance(payload, dict):
            raise AssemblyApiError(f"{self.LABEL} API returned a malformed response")
        rows, total_count, result_code = self._response_parts(payload)
        for row in rows:
            if _required(row, "CONF_ID", label=self.LABEL) != self.meeting_id:
                raise AssemblyApiError(f"{self.LABEL} row CONF_ID is inconsistent")
        body = json.dumps(
            self._safe_payload(rows, total_count, result_code),
            ensure_ascii=False,
            sort_keys=True,
        )
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="국회 국회사무처",
            published_at=None,
            body=body,
            metadata={
                "api_code": self.API_CODE,
                "meeting_id": self.meeting_id,
                "page_index": query.get("pIndex", "1"),
                "page_size": query.get("pSize", "100"),
                "row_count": str(len(rows)),
                "list_total_count": "" if total_count is None else str(total_count),
                "result_code": result_code or "",
                "sample_mode": str(self.sample_mode).lower(),
            },
        )


class OpenAssemblyMeetingDetailConnector(_OpenAssemblyMeetingConnector):
    API_CODE = "VCONFDETAIL"
    LABEL = "National Assembly meeting-detail"
    TITLE = "국회 국회사무처_회의록별 상세정보"
    SAFE_FIELDS = (
        "CONF_ID",
        "ERACO",
        "SESS",
        "DGR",
        "CONF_DT",
        "CONF_KND",
        "CMIT_NM",
        "SB_CMIT_NM",
        "CONF_PLC",
        "BG_PTM",
        "ED_PTM",
        "CONF_PTM",
        "HR_HRG_YN",
        "PBHRG_YN",
        "HRG_YN",
        "SITG_YN",
        "RMND_SPH_YN",
        "RDJM_SPH_YN",
        "FRNGUS_SPH_YN",
        "DOWN_URL",
    )

    @classmethod
    def _safe_row(cls, row: dict) -> dict[str, object]:
        safe = super()._safe_row(row)
        safe["DOWN_URL"] = _sanitized_url(_optional(row, "DOWN_URL"))
        return safe

    def parse_detail(self, document: ConnectorDocument) -> AssemblyMeetingDetailRecord:
        payload = _load_document(document, self.LABEL)
        rows, _, _ = self._response_parts(payload)
        if len(rows) != 1:
            raise AssemblyApiError("meeting-detail source must return exactly one row")
        row = rows[0]
        return AssemblyMeetingDetailRecord(
            meeting_id=_required(row, "CONF_ID", label=self.LABEL),
            assembly_term=_required(row, "ERACO", label=self.LABEL),
            session=_required(row, "SESS", label=self.LABEL),
            degree=_required(row, "DGR", label=self.LABEL),
            meeting_date=_date_value(row, "CONF_DT", label=self.LABEL),
            meeting_kind=_required(row, "CONF_KND", label=self.LABEL),
            committee_name=_required(row, "CMIT_NM", label=self.LABEL),
            subcommittee_name=_optional(row, "SB_CMIT_NM"),
            place=_optional(row, "CONF_PLC"),
            start_time=_optional(row, "BG_PTM"),
            end_time=_optional(row, "ED_PTM"),
            duration=_optional(row, "CONF_PTM"),
            personnel_hearing=_yn(row, "HR_HRG_YN", label=self.LABEL),
            public_hearing=_yn(row, "PBHRG_YN", label=self.LABEL),
            hearing=_yn(row, "HRG_YN", label=self.LABEL),
            joint_meeting=_yn(row, "SITG_YN", label=self.LABEL),
            presidential_delegated_speech=_yn(
                row, "RMND_SPH_YN", label=self.LABEL
            ),
            presidential_policy_speech=_yn(
                row, "RDJM_SPH_YN", label=self.LABEL
            ),
            foreign_guest_speech=_yn(row, "FRNGUS_SPH_YN", label=self.LABEL),
            minutes_download_url=_sanitized_url(_optional(row, "DOWN_URL")),
        )


class OpenAssemblyMeetingAgendaConnector(_OpenAssemblyMeetingConnector):
    API_CODE = "VCONFBLLLIST"
    LABEL = "National Assembly meeting-agenda"
    TITLE = "국회 국회사무처_회의별 안건목록"
    SAFE_FIELDS = (
        "CONF_ID",
        "ERACO",
        "SESS",
        "DGR",
        "BLL_NO",
        "BLL_NM",
        "BLL_LV",
    )

    def parse_agendas(
        self, document: ConnectorDocument
    ) -> tuple[AssemblyMeetingAgendaRecord, ...]:
        payload = _load_document(document, self.LABEL)
        rows, _, _ = self._response_parts(payload)
        return tuple(
            AssemblyMeetingAgendaRecord(
                meeting_id=_required(row, "CONF_ID", label=self.LABEL),
                assembly_term=_required(row, "ERACO", label=self.LABEL),
                session=_required(row, "SESS", label=self.LABEL),
                degree=_required(row, "DGR", label=self.LABEL),
                agenda_no=_required_int(row, "BLL_NO", label=self.LABEL),
                agenda_name=_required(row, "BLL_NM", label=self.LABEL),
                agenda_level=_required_int(row, "BLL_LV", label=self.LABEL),
            )
            for row in rows
        )


class OpenAssemblyMeetingBillConnector(_OpenAssemblyMeetingConnector):
    API_CODE = "VCONFBILLLIST"
    LABEL = "National Assembly meeting-bill"
    TITLE = "국회 국회사무처_회의별 의안목록"
    SAFE_FIELDS = (
        "CONF_ID",
        "ERACO",
        "SESS",
        "DGR",
        "BILL_ID",
        "BILL_NM",
        "LINK_URL",
    )

    def __init__(
        self,
        *,
        meeting_id: str,
        bill_id: str | None = None,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 100,
        sample_mode: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            meeting_id=meeting_id,
            api_key=api_key,
            page_index=page_index,
            page_size=page_size,
            sample_mode=sample_mode,
            transport=transport,
        )
        self.bill_id = bill_id.strip() if bill_id else None

    @property
    def has_bill_filter(self) -> bool:
        return self.bill_id is not None

    def _query_params(self) -> dict[str, str]:
        params = super()._query_params()
        if self.bill_id:
            params["BILL_ID"] = self.bill_id
        return params

    EXTRA_FILTERS = frozenset({"BILL_ID"})

    @classmethod
    def _safe_row(cls, row: dict) -> dict[str, object]:
        safe = super()._safe_row(row)
        safe["LINK_URL"] = _sanitized_url(_optional(row, "LINK_URL"))
        return safe

    def parse_bills(
        self, document: ConnectorDocument
    ) -> tuple[AssemblyMeetingBillRecord, ...]:
        payload = _load_document(document, self.LABEL)
        rows, _, _ = self._response_parts(payload)
        return tuple(
            AssemblyMeetingBillRecord(
                meeting_id=_required(row, "CONF_ID", label=self.LABEL),
                assembly_term=_required(row, "ERACO", label=self.LABEL),
                session=_required(row, "SESS", label=self.LABEL),
                degree=_required(row, "DGR", label=self.LABEL),
                bill_id=_required(row, "BILL_ID", label=self.LABEL),
                bill_name=_required(row, "BILL_NM", label=self.LABEL),
                link_url=_sanitized_url(_optional(row, "LINK_URL")),
            )
            for row in rows
        )


def _load_document(document: ConnectorDocument, label: str) -> dict:
    try:
        payload = json.loads(document.body)
    except json.JSONDecodeError:
        raise AssemblyApiError(f"{label} document is not valid JSON") from None
    if not isinstance(payload, dict):
        raise AssemblyApiError(f"{label} document is malformed")
    return payload
