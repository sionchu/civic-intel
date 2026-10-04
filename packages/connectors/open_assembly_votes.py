"""National Assembly plenary roll-call vote connectors (열린국회정보).

Two official Open Assembly APIs bound one Assembly term's roll-call universe:

* ``ncocpgfiaoituanbr`` (의안별 표결현황): one row per plenary-voted bill with published
  tallies. Requires ``AGE``.
* ``nojepdqqaweusdfbi`` (국회의원 본회의 표결정보): one row per seated member for one bill.
  Requires ``AGE`` and ``BILL_ID``.

Both were verified with keyless sample requests on 2026-10-04; see
docs/architecture/ASSEMBLY_ROLL_CALL_VOTE_FEEDER.md. Display names, Hanja names, party and
district fields are published by the provider but are deliberately not parsed here.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import ClassVar
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from packages.connectors.open_assembly import POLICY_ID as ASSEMBLY_SOURCE_POLICY_ID
from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument
from .open_assembly import AssemblyApiError, MissingAssemblyApiKey

# Every Open Assembly API lane shares the host-level SourcePolicy row (one policy per domain).
POLICY_ID = ASSEMBLY_SOURCE_POLICY_ID

class RollCallVoteValue(StrEnum):
    """Closed mapping of the provider's published RESULT_VOTE_MOD values.

    ``NOT_PARTICIPATING`` (불참) records that no vote was cast. It is never a NO vote and no
    reason (absence, walk-out, boycott, leave) is inferred from it.
    """

    YES = "YES"
    NO = "NO"
    ABSTAIN = "ABSTAIN"
    NOT_PARTICIPATING = "NOT_PARTICIPATING"


PUBLISHED_VOTE_VALUES: dict[str, RollCallVoteValue] = {
    "찬성": RollCallVoteValue.YES,
    "반대": RollCallVoteValue.NO,
    "기권": RollCallVoteValue.ABSTAIN,
    "불참": RollCallVoteValue.NOT_PARTICIPATING,
}


class AssemblyRollCallContractError(AssemblyApiError):
    """A provider row violates the verified roll-call row contract."""


def national_assembly_roll_call_vote_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 10, 4, tzinfo=UTC)
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
            "Provider-controlled traffic; development auto-approval, operation review approval"
        ),
        policy_note=(
            "Reviewed 2026-10-04 against the Open Assembly service page OPR1MQ000998LC12535 "
            "(국회의원 본회의 표결정보, API nojepdqqaweusdfbi; origin 의안정보시스템 표결정보; "
            "file/API scope 20th Assembly onward), data.go.kr dataset 15125948 and the bill-level "
            "의안별 표결현황 API ncocpgfiaoituanbr. Civic Intel stores member-code-linked vote "
            "facts only; no names, party, district, contact fields or detail-HTML scraping."
        ),
    )


@dataclass(frozen=True)
class AssemblyBillVoteSummary:
    """One plenary-voted bill row with the provider's published tallies."""

    bill_id: str
    assembly_age: int
    bill_no: str | None
    bill_name: str | None
    processed_date: date | None
    committee: str | None
    committee_id: str | None
    process_result: str | None
    bill_kind: str | None
    member_total: int
    vote_total: int
    yes_total: int
    no_total: int
    abstain_total: int
    link_url: str | None

    def fingerprint_fields(self) -> dict[str, object]:
        return {
            "bill_id": self.bill_id,
            "assembly_age": self.assembly_age,
            "member_total": self.member_total,
            "vote_total": self.vote_total,
            "yes_total": self.yes_total,
            "no_total": self.no_total,
            "abstain_total": self.abstain_total,
        }


@dataclass(frozen=True)
class AssemblyMemberVoteRecord:
    """One member's published plenary vote on one bill (identity = provider MONA_CD)."""

    bill_id: str
    assembly_age: int
    member_code: str
    vote_value_published: str
    vote_value: RollCallVoteValue
    vote_datetime_published: str
    vote_datetime: datetime
    bill_no: str | None
    bill_name: str | None
    session_code: str | None
    sitting_number: str | None
    committee: str | None
    committee_id: str | None
    bill_url: str | None

    @property
    def provider_record_key(self) -> str:
        return f"{self.bill_id}:{self.member_code}"


def _optional(row: dict, key: str) -> str | None:
    value = row.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _required_int(row: dict, key: str) -> int:
    value = row.get(key)
    if isinstance(value, bool) or value is None:
        raise AssemblyRollCallContractError(f"vote summary row lacks integer {key}")
    try:
        number = int(str(value).strip())
    except ValueError:
        raise AssemblyRollCallContractError(f"vote summary row lacks integer {key}") from None
    if number < 0:
        raise AssemblyRollCallContractError(f"vote summary row has negative {key}")
    return number


def _age(row: dict) -> int:
    text = _optional(row, "AGE")
    if not text:
        raise AssemblyRollCallContractError("roll-call row lacks AGE")
    try:
        return int(text)
    except ValueError:
        raise AssemblyRollCallContractError("roll-call row has invalid AGE") from None


def _iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.replace(".", "-").replace("/", "-"))
    except ValueError:
        return None


def parse_vote_datetime(value: str | None) -> datetime:
    """Parse the provider's ``YYYYMMDD HHMMSS`` VOTE_DATE as Korea Standard Time."""

    if not value:
        raise AssemblyRollCallContractError("member vote row lacks VOTE_DATE")
    try:
        # The provider publishes Korea Standard Time without an offset.
        return datetime.strptime(f"{value.strip()} +0900", "%Y%m%d %H%M%S %z")
    except ValueError:
        raise AssemblyRollCallContractError("member vote row has malformed VOTE_DATE") from None


class _OpenAssemblyRollCallApi(Connector):
    """Shared credential, URL validation and response-envelope handling."""

    API_CODE: ClassVar[str]
    TITLE: ClassVar[str]
    HOST: ClassVar[str] = "open.assembly.go.kr"
    REQUIRED_QUERY: ClassVar[frozenset[str]]
    ALLOWED_QUERY: ClassVar[frozenset[str]]

    def __init__(
        self,
        *,
        assembly_age: int,
        api_key: str | None,
        page_index: int,
        page_size: int,
        transport: httpx.BaseTransport | None,
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
        self._transport = transport

    @classmethod
    def base_url(cls) -> str:
        return f"https://{cls.HOST}/portal/openapi/{cls.API_CODE}"

    @classmethod
    def path(cls) -> str:
        return f"/portal/openapi/{cls.API_CODE}"

    def _credential(self) -> str:
        value = self._api_key or os.getenv("ASSEMBLY_API_KEY")
        if not value:
            raise MissingAssemblyApiKey("ASSEMBLY_API_KEY is required for live fetch")
        return value

    def _query(self) -> dict[str, str]:
        return {
            "Type": "json",
            "pIndex": str(self.page_index),
            "pSize": str(self.page_size),
            "AGE": str(self.assembly_age),
        }

    def discover(self) -> list[str]:
        return [f"{self.base_url()}?{urlencode(self._query())}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.path():
            raise ValueError("unsupported National Assembly roll-call API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if any(key.casefold() in {"key", "authkey", "servicekey"} for key in raw):
            raise ValueError("credentials must not be embedded in connector URLs")
        if set(raw) - cls.ALLOWED_QUERY:
            raise ValueError("unsupported National Assembly roll-call API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("Type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        for key in cls.REQUIRED_QUERY:
            if not query.get(key):
                raise ValueError(f"{key} is required for National Assembly roll-call API")
        return query

    @classmethod
    def _redact_credentials(cls, value):
        if isinstance(value, dict):
            return {
                key: cls._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"key", "authkey", "servicekey"}
            }
        if isinstance(value, list):
            return [cls._redact_credentials(item) for item in value]
        return value

    @classmethod
    def response_parts(cls, payload: dict) -> tuple[list[dict], int | None, str | None]:
        # Errors and empty results arrive as a top-level RESULT without the API-code block.
        top_result = payload.get("RESULT")
        if cls.API_CODE not in payload and isinstance(top_result, dict):
            code = str(top_result.get("CODE") or "")
            if code == "INFO-200":
                return [], 0, code
            raise AssemblyApiError(f"National Assembly roll-call API returned {code or 'error'}")
        blocks = payload.get(cls.API_CODE)
        if not isinstance(blocks, list) or not blocks:
            raise AssemblyApiError("National Assembly roll-call API returned a malformed response")

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
        if result_code not in {None, "", "INFO-000"}:
            raise AssemblyApiError(f"National Assembly roll-call API returned {result_code}")
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
                response = client.get(self.base_url(), params=request_params)
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError, json.JSONDecodeError):
            raise AssemblyApiError("National Assembly roll-call API request failed") from None

        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly roll-call API returned a malformed response")
        payload = self._redact_credentials(payload)
        rows, total_count, result_code = self.response_parts(payload)
        metadata = {
            "api_code": self.API_CODE,
            "assembly_age": query["AGE"],
            "page_index": query.get("pIndex", "1"),
            "page_size": query.get("pSize", "100"),
            "row_count": str(len(rows)),
            "list_total_count": "" if total_count is None else str(total_count),
            "result_code": result_code or "",
        }
        for key in sorted(self.ALLOWED_QUERY - {"Type", "pIndex", "pSize", "AGE"}):
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="국회 국회사무처",
            published_at=None,
            body=json.dumps(payload, ensure_ascii=False, sort_keys=True),
            metadata=metadata,
        )

    @classmethod
    def _document_rows(cls, document: ConnectorDocument) -> list[dict]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise AssemblyApiError("National Assembly roll-call document is not valid JSON") from None
        if not isinstance(payload, dict):
            raise AssemblyApiError("National Assembly roll-call document is malformed")
        rows, _, _ = cls.response_parts(payload)
        return rows


class OpenAssemblyBillVoteSummaryConnector(_OpenAssemblyRollCallApi):
    """의안별 표결현황: the bounded list of plenary-voted bills for one Assembly term."""

    API_CODE = "ncocpgfiaoituanbr"
    TITLE = "국회 국회사무처_의안별 표결현황 API"
    REQUIRED_QUERY = frozenset({"AGE"})
    ALLOWED_QUERY = frozenset({"Type", "pIndex", "pSize", "AGE"})

    def __init__(
        self,
        *,
        assembly_age: int,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 1000,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            assembly_age=assembly_age,
            api_key=api_key,
            page_index=page_index,
            page_size=page_size,
            transport=transport,
        )

    def for_page(self, page_index: int) -> OpenAssemblyBillVoteSummaryConnector:
        return OpenAssemblyBillVoteSummaryConnector(
            assembly_age=self.assembly_age,
            api_key=self._api_key,
            page_index=page_index,
            page_size=self.page_size,
            transport=self._transport,
        )

    def member_votes(self, bill_id: str, *, page_size: int) -> OpenAssemblyMemberVoteConnector:
        return OpenAssemblyMemberVoteConnector(
            assembly_age=self.assembly_age,
            bill_id=bill_id,
            api_key=self._api_key,
            page_size=page_size,
            transport=self._transport,
        )

    @classmethod
    def parse_summaries(cls, document: ConnectorDocument) -> list[AssemblyBillVoteSummary]:
        summaries: list[AssemblyBillVoteSummary] = []
        for row in cls._document_rows(document):
            bill_id = _optional(row, "BILL_ID")
            if not bill_id:
                raise AssemblyRollCallContractError("vote summary row lacks BILL_ID")
            summaries.append(
                AssemblyBillVoteSummary(
                    bill_id=bill_id,
                    assembly_age=_age(row),
                    bill_no=_optional(row, "BILL_NO"),
                    bill_name=_optional(row, "BILL_NAME"),
                    processed_date=_iso_date(_optional(row, "PROC_DT")),
                    committee=_optional(row, "CURR_COMMITTEE"),
                    committee_id=_optional(row, "CURR_COMMITTEE_ID"),
                    process_result=_optional(row, "PROC_RESULT_CD"),
                    bill_kind=_optional(row, "BILL_KIND_CD"),
                    member_total=_required_int(row, "MEMBER_TCNT"),
                    vote_total=_required_int(row, "VOTE_TCNT"),
                    yes_total=_required_int(row, "YES_TCNT"),
                    no_total=_required_int(row, "NO_TCNT"),
                    abstain_total=_required_int(row, "BLANK_TCNT"),
                    link_url=_optional(row, "LINK_URL"),
                )
            )
        return summaries


class OpenAssemblyMemberVoteConnector(_OpenAssemblyRollCallApi):
    """국회의원 본회의 표결정보: every seated member's published vote on one bill."""

    API_CODE = "nojepdqqaweusdfbi"
    TITLE = "국회 국회사무처_국회의원 본회의 표결정보 API"
    REQUIRED_QUERY = frozenset({"AGE", "BILL_ID"})
    ALLOWED_QUERY = frozenset({"Type", "pIndex", "pSize", "AGE", "BILL_ID"})

    def __init__(
        self,
        *,
        assembly_age: int,
        bill_id: str,
        api_key: str | None = None,
        page_index: int = 1,
        page_size: int = 1000,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(
            assembly_age=assembly_age,
            api_key=api_key,
            page_index=page_index,
            page_size=page_size,
            transport=transport,
        )
        cleaned = bill_id.strip()
        if not cleaned or any(char.isspace() for char in cleaned):
            raise ValueError("bill_id must be a non-empty provider BILL_ID")
        self.bill_id = cleaned

    def _query(self) -> dict[str, str]:
        return super()._query() | {"BILL_ID": self.bill_id}

    @classmethod
    def parse_votes(cls, document: ConnectorDocument) -> list[AssemblyMemberVoteRecord]:
        records: list[AssemblyMemberVoteRecord] = []
        for row in cls._document_rows(document):
            bill_id = _optional(row, "BILL_ID")
            member_code = _optional(row, "MONA_CD")
            if not bill_id or not member_code:
                raise AssemblyRollCallContractError(
                    "member vote row lacks BILL_ID or MONA_CD identity fields"
                )
            if any(char.isspace() or char == ":" for char in member_code):
                raise AssemblyRollCallContractError("member vote row has malformed MONA_CD")
            published = _optional(row, "RESULT_VOTE_MOD")
            if published is None or published not in PUBLISHED_VOTE_VALUES:
                raise AssemblyRollCallContractError(
                    "member vote row has an unknown RESULT_VOTE_MOD value"
                )
            vote_datetime_published = _optional(row, "VOTE_DATE") or ""
            records.append(
                AssemblyMemberVoteRecord(
                    bill_id=bill_id,
                    assembly_age=_age(row),
                    member_code=member_code,
                    vote_value_published=published,
                    vote_value=PUBLISHED_VOTE_VALUES[published],
                    vote_datetime_published=vote_datetime_published,
                    vote_datetime=parse_vote_datetime(vote_datetime_published),
                    bill_no=_optional(row, "BILL_NO"),
                    bill_name=_optional(row, "BILL_NAME"),
                    session_code=_optional(row, "SESSION_CD"),
                    sitting_number=_optional(row, "CURRENTS_CD"),
                    committee=_optional(row, "CURR_COMMITTEE"),
                    committee_id=_optional(row, "CURR_COMMITTEE_ID"),
                    bill_url=_optional(row, "BILL_URL"),
                )
            )
        return records
