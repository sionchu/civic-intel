from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from uuid import UUID

import httpx

from packages.domain.contracts import SourcePolicy
from packages.domain.enums import SourceCollectionMode

from .base import Connector, ConnectorDocument


class MoisOrganizationCodeApiError(RuntimeError):
    pass


class MissingMoisOrganizationCodeApiKey(MoisOrganizationCodeApiError):
    pass


POLICY_ID = UUID("25aa95dd-a30b-5835-bc83-f91d80a54efd")

def mois_organization_code_policy() -> SourcePolicy:
    reviewed_at = datetime(2026, 9, 22, tzinfo=UTC)
    return SourcePolicy(
        id=POLICY_ID,
        domain="apis.data.go.kr",
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
            "Development account 10,000 requests; operation account auto-approved; "
            "higher traffic may require a registered use case"
        ),
        policy_note=(
            "Reviewed against data.go.kr dataset 15077870 on 2026-09-22. "
            "Current institutions only; org_cd is a provider Organization key, not a "
            "canonical Civic Intel Organization ID or automatic Gukgam binding authority."
        ),
    )

@dataclass(frozen=True)
class MoisOrganizationCodeRecord:
    org_code: str
    full_name: str | None
    lowest_name: str | None
    abbreviation: str | None
    gap_no: str | None
    rank_no: str | None
    sub_chasu: str | None
    parent_org_code: str | None
    top_org_code: str | None
    representative_org_code: str | None
    type_big: str | None
    type_mid: str | None
    type_small: str | None
    location_standard_code: str | None
    use_code: str | None
    created_date: date | None
    closed_date: date | None
    stop_selector: str
    changed_date: date | None
    base_date: date | None
    applied_date: date | None
    previous_org_code: str | None

class MoisOrganizationCodeConnector(Connector):
    HOST = "apis.data.go.kr"
    PATH = "/1741000/StanOrgCd2/getStanOrgCdList2"
    BASE_URL = f"https://{HOST}{PATH}"
    TITLE = "행정안전부_행정표준코드_기관코드"
    ALLOWED_QUERY: ClassVar[frozenset[str]] = frozenset(
        {"pageNo", "numOfRows", "type", "full_nm", "org_cd", "stop_selt"}
    )

    def __init__(
        self,
        *,
        api_key: str | None = None,
        page_no: int = 1,
        page_size: int = 100,
        full_name: str | None = None,
        org_code: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if page_no < 1:
            raise ValueError("page_no must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        if org_code is not None and (len(org_code) != 7 or not org_code.isdigit()):
            raise ValueError("org_code must be a seven-digit provider code")
        self._api_key = api_key
        self.page_no = page_no
        self.page_size = page_size
        self.full_name = full_name
        self.org_code = org_code
        self._transport = transport

    def _credential(self) -> str:
        value = self._api_key or os.getenv("MOIS_ORG_CODE_API_KEY")
        if not value:
            raise MissingMoisOrganizationCodeApiKey(
                "MOIS_ORG_CODE_API_KEY is required for live fetch"
            )
        return unquote(value)

    def discover(self) -> list[str]:
        params: dict[str, str] = {
            "pageNo": str(self.page_no),
            "numOfRows": str(self.page_size),
            "type": "json",
            "stop_selt": "0",
        }
        if self.full_name:
            params["full_nm"] = self.full_name
        if self.org_code:
            params["org_cd"] = self.org_code
        return [f"{self.BASE_URL}?{urlencode(params)}"]

    @classmethod
    def _validated_query(cls, url: str) -> dict[str, str]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.netloc != cls.HOST or parsed.path != cls.PATH:
            raise ValueError("unsupported MOIS organization-code API URL")
        raw = parse_qs(parsed.query, keep_blank_values=True)
        if {key.casefold() for key in raw} & {"servicekey", "key", "authkey"}:
            raise ValueError("credentials must not be embedded in connector URLs")
        unknown = set(raw) - cls.ALLOWED_QUERY
        if unknown:
            raise ValueError("unsupported MOIS organization-code API query parameter")
        query = {key: values[-1] for key, values in raw.items()}
        if query.get("type", "json").lower() != "json":
            raise ValueError("connector requires JSON responses")
        if query.get("stop_selt") != "0":
            raise ValueError("connector is current-institution only and requires stop_selt=0")
        try:
            page_no = int(query.get("pageNo", "1"))
            page_size = int(query.get("numOfRows", "100"))
        except ValueError:
            raise ValueError("pageNo and numOfRows must be integers") from None
        if page_no < 1 or not 1 <= page_size <= 1000:
            raise ValueError("invalid MOIS organization-code pagination")
        org_code = query.get("org_cd")
        if org_code is not None and (len(org_code) != 7 or not org_code.isdigit()):
            raise ValueError("org_cd must be a seven-digit provider code")
        return query

    @staticmethod
    def _redact_credentials(value):
        if isinstance(value, dict):
            return {
                key: MoisOrganizationCodeConnector._redact_credentials(item)
                for key, item in value.items()
                if key.casefold() not in {"servicekey", "key", "authkey"}
            }
        if isinstance(value, list):
            return [MoisOrganizationCodeConnector._redact_credentials(item) for item in value]
        return value

    @classmethod
    def _response_parts(
        cls, payload: dict
    ) -> tuple[list[dict], int | None, int | None, int | None, str | None]:
        response = payload.get("response")
        if not isinstance(response, dict):
            legacy = payload.get("StanOrgCd")
            if not isinstance(legacy, list) or not legacy:
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code API returned a malformed response"
                )
            legacy_result_code: str | None = None
            legacy_total_count: int | None = None
            legacy_page_no: int | None = None
            legacy_page_size: int | None = None
            legacy_rows: list[dict] = []
            for block in legacy:
                if not isinstance(block, dict):
                    continue
                head = block.get("head")
                if isinstance(head, list):
                    for item in head:
                        if not isinstance(item, dict):
                            continue
                        if "totalCount" in item:
                            legacy_total_count = cls._optional_int(
                                item.get("totalCount"), "totalCount"
                            )
                        if "pageNo" in item:
                            legacy_page_no = cls._optional_int(item.get("pageNo"), "pageNo")
                        if "numOfRows" in item:
                            legacy_page_size = cls._optional_int(
                                item.get("numOfRows"), "numOfRows"
                            )
                        result = item.get("RESULT")
                        if isinstance(result, dict):
                            legacy_result_code = str(result.get("resultCode") or "")
                candidate_rows = block.get("row")
                if isinstance(candidate_rows, list):
                    if any(not isinstance(item, dict) for item in candidate_rows):
                        raise MoisOrganizationCodeApiError(
                            "MOIS organization-code API returned malformed row"
                        )
                    legacy_rows.extend(candidate_rows)
            if legacy_result_code not in {None, "", "0", "00", "INFO-0", "INFO-000"}:
                raise MoisOrganizationCodeApiError(
                    f"MOIS organization-code API returned {legacy_result_code}"
                )
            return (
                legacy_rows,
                legacy_total_count,
                legacy_page_no,
                legacy_page_size,
                legacy_result_code,
            )
        header = response.get("header")
        result_code: str | None = None
        if isinstance(header, dict):
            result_code = str(header.get("resultCode") or "")
            if result_code not in {"", "0", "00", "INFO-0", "INFO-000"}:
                raise MoisOrganizationCodeApiError(
                    f"MOIS organization-code API returned {result_code}"
                )
        body = response.get("body")
        if not isinstance(body, dict):
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code API returned a malformed body"
            )
        total_count = cls._optional_int(body.get("totalCount"), "totalCount")
        provider_page_no = cls._optional_int(body.get("pageNo"), "pageNo")
        provider_page_size = cls._optional_int(body.get("numOfRows"), "numOfRows")
        items = body.get("items")
        if items in (None, ""):
            return [], total_count, provider_page_no, provider_page_size, result_code
        if isinstance(items, dict):
            candidate_rows = items.get("item", [])
        elif isinstance(items, list):
            candidate_rows = items
        else:
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code API returned malformed items"
            )
        if isinstance(candidate_rows, dict):
            rows = [candidate_rows]
        elif isinstance(candidate_rows, list):
            if any(not isinstance(item, dict) for item in candidate_rows):
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code API returned malformed row"
                )
            rows = list(candidate_rows)
        else:
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code API returned malformed rows"
            )
        return rows, total_count, provider_page_no, provider_page_size, result_code

    @staticmethod
    def _optional_int(value: object, field: str) -> int | None:
        if value in (None, ""):
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            raise MoisOrganizationCodeApiError(
                f"MOIS organization-code API returned invalid {field}"
            ) from None

    def fetch(self, url: str) -> ConnectorDocument:
        query = self._validated_query(url)
        request_params = query | {"ServiceKey": self._credential()}
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
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code API request failed"
            ) from None
        if not isinstance(payload, dict):
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code API returned a malformed response"
            )
        payload = self._redact_credentials(payload)
        rows, total_count, provider_page_no, provider_page_size, result_code = (
            self._response_parts(payload)
        )
        metadata = {
            "source_contract": "mois_standard_organization_code_v1",
            "page_no": query.get("pageNo", "1"),
            "page_size": query.get("numOfRows", "100"),
            "row_count": str(len(rows)),
            "total_count": "" if total_count is None else str(total_count),
            "provider_page_no": "" if provider_page_no is None else str(provider_page_no),
            "provider_page_size": (
                "" if provider_page_size is None else str(provider_page_size)
            ),
            "result_code": result_code or "",
            "stop_selt": "0",
        }
        for key in ("full_nm", "org_cd"):
            if key in query:
                metadata[key] = query[key]
        return ConnectorDocument(
            url=url,
            title=self.TITLE,
            publisher="행정안전부",
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
    def _optional_date(cls, row: dict, key: str) -> date | None:
        value = cls._optional(row, key)
        if value is None:
            return None
        if len(value) != 8 or not value.isdigit():
            raise MoisOrganizationCodeApiError(
                f"MOIS organization-code row has invalid {key}"
            )
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        except ValueError:
            raise MoisOrganizationCodeApiError(
                f"MOIS organization-code row has invalid {key}"
            ) from None

    @staticmethod
    def _validate_code(value: str | None, field: str) -> str | None:
        if value is None:
            return None
        if len(value) != 7 or not value.isdigit():
            raise MoisOrganizationCodeApiError(
                f"MOIS organization-code row has invalid {field}"
            )
        return value

    @classmethod
    def parse_organizations(
        cls, document: ConnectorDocument
    ) -> list[MoisOrganizationCodeRecord]:
        try:
            payload = json.loads(document.body)
        except json.JSONDecodeError:
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code document is not valid JSON"
            ) from None
        if not isinstance(payload, dict):
            raise MoisOrganizationCodeApiError(
                "MOIS organization-code document is malformed"
            )
        rows, _, _, _, _ = cls._response_parts(payload)
        records: list[MoisOrganizationCodeRecord] = []
        seen: set[str] = set()
        for row in rows:
            org_code = cls._validate_code(cls._optional(row, "org_cd"), "org_cd")
            if org_code is None:
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code row lacks org_cd"
                )
            if org_code in seen:
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code response contains duplicate org_cd"
                )
            seen.add(org_code)
            full_name = cls._optional(row, "full_nm")
            lowest_name = cls._optional(row, "low_nm")
            if full_name is None and lowest_name is None:
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code row lacks organization name"
                )
            stop_selector = cls._optional(row, "stop_selt") or "0"
            if stop_selector != "0":
                raise MoisOrganizationCodeApiError(
                    "MOIS organization-code connector accepts current rows only"
                )
            records.append(
                MoisOrganizationCodeRecord(
                    org_code=org_code,
                    full_name=full_name,
                    lowest_name=lowest_name,
                    abbreviation=cls._optional(row, "abbr_nm"),
                    gap_no=cls._optional(row, "gap_no"),
                    rank_no=cls._optional(row, "rank_no"),
                    sub_chasu=cls._optional(row, "sub_chasu"),
                    parent_org_code=cls._validate_code(
                        cls._optional(row, "high_cd"), "high_cd"
                    ),
                    top_org_code=cls._validate_code(
                        cls._optional(row, "highst_cd"), "highst_cd"
                    ),
                    representative_org_code=cls._validate_code(
                        cls._optional(row, "rep_cd"), "rep_cd"
                    ),
                    type_big=cls._optional(row, "typebig_nm"),
                    type_mid=cls._optional(row, "typemid_nm"),
                    type_small=cls._optional(row, "typesml_nm"),
                    location_standard_code=cls._optional(row, "locatstd_cd"),
                    use_code=cls._optional(row, "use_cd"),
                    created_date=cls._optional_date(row, "crt_de"),
                    closed_date=cls._optional_date(row, "cls_de"),
                    stop_selector=stop_selector,
                    changed_date=cls._optional_date(row, "chg_de"),
                    base_date=cls._optional_date(row, "base_date"),
                    applied_date=cls._optional_date(row, "adpt_date"),
                    previous_org_code=cls._optional(row, "preorg_cd"),
                )
            )
        return records
